<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAnalysis } from '../composables/useAnalysis'

const { completedNodes, report, needsReview, running, chatHistory, chatLoading, analyze, resume, chat, restoreSession, cancel, NODE_LABELS } = useAnalysis()

onMounted(() => restoreSession())
onUnmounted(() => { if (running.value) cancel() })
const policyId = ref('policy-001')
const file = ref(null)
const chatInput = ref('')

const ingesting = ref(false)
const ingestLog = ref([])
const ingestTotal = ref(Number(sessionStorage.getItem('rw_ingest_total')) || 0)
const ingestDone = ref(sessionStorage.getItem('rw_ingest_done') === '1')

// progress entries are those with status 'ok' or 'error' (excludes the final 'done' summary)
const ingestProgress = computed(() => ingestLog.value.filter(e => e.status !== 'done').length)
const ingestPct = computed(() =>
  ingestTotal.value ? Math.round(ingestProgress.value / ingestTotal.value * 100) : 0
)

async function runIngest() {
  ingesting.value = true
  ingestLog.value = []
  ingestTotal.value = 0
  ingestDone.value = false
  try {
    const resp = await fetch('/ingest', { method: 'POST' })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const block = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        if (!block.includes('data:')) continue
        const ev = (block.match(/event: (.*)/) || [])[1]
        let data
        try { data = JSON.parse((block.match(/data: (.*)/) || [])[1] || '{}') } catch { continue }
        if (ev === 'progress') ingestLog.value.push(data)
        if (ev === 'done') {
          ingestTotal.value = data.total   // set total from API — no hardcoding
          ingestLog.value.push({ regulation: '—', status: 'done', detail: data.message })
          ingestDone.value = true
          sessionStorage.setItem('rw_ingest_done', '1')
          sessionStorage.setItem('rw_ingest_total', data.total)
        }
      }
    }
  } catch (e) {
    ingestLog.value.push({ regulation: '—', status: 'error', detail: e.message })
  }
  ingesting.value = false
}

// Deduplicate: tools_node / collect_tool_results alias to 'Tools' — keep each label once
const PIPELINE = [...new Set(Object.values(NODE_LABELS))]

function onFile(e) { file.value = e.target.files[0] }
function submit() { if (file.value) analyze(file.value, policyId.value) }
function sendChat() {
  const q = chatInput.value.trim()
  if (!q || chatLoading.value) return
  chatInput.value = ''
  chat(q)
}

function isActive(step, i) {
  if (completedNodes.value.includes(step)) return false
  if (!running.value) return false
  return completedNodes.value.length === i
}

</script>

<template>
  <div class="rw-app">
    <!-- Sidebar -->
    <aside class="rw-sidebar">
      <div class="rw-brand">
        <span class="rw-brand-mark">RW</span>
        <div>
          <div class="rw-brand-name">RegWatch</div>
          <div class="rw-brand-sub">Compliance</div>
        </div>
      </div>

      <div class="rw-sidebar-section">
        <div class="rw-sidebar-label">Pipeline</div>
        <ul class="rw-sidebar-pipeline">
          <li
            v-for="step in PIPELINE"
            :key="step"
            class="rw-sidebar-step"
            :class="{ done: completedNodes.includes(step) }"
          >
            <span class="rw-sidebar-dot"></span>
            {{ step }}
          </li>
        </ul>
      </div>

    </aside>

    <!-- Main content -->
    <main class="rw-main">
      <header class="rw-header">
        <div>
          <p class="rw-eyebrow">Plataforma de análisis</p>
          <h1 class="rw-title">Análisis de Compliance</h1>
        </div>
        <div v-if="running" class="rw-running-badge">
          <span class="rw-pulse"></span> Analizando
          <button class="rw-btn-stop" @click="cancel" title="Detener análisis">✕ Detener</button>
        </div>
      </header>

      <!-- Upload card -->
      <section class="rw-card rw-upload">
        <div class="rw-upload-fields">
          <div class="rw-field">
            <label class="rw-field-label" for="policy-id">Policy ID</label>
            <input
              id="policy-id"
              class="rw-input"
              v-model="policyId"
              placeholder="policy-001"
            />
          </div>

          <div class="rw-field rw-field-file">
            <label class="rw-field-label">Documento</label>
            <label class="rw-file-drop" :class="{ 'has-file': file }">
              <input type="file" accept="application/pdf" @change="onFile" />
              <svg class="rw-file-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 4a2 2 0 012-2h5l5 5v9a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/>
                <path d="M13 2v5h5"/>
              </svg>
              <span>{{ file ? file.name : 'Seleccionar PDF…' }}</span>
            </label>
          </div>
        </div>

        <button class="rw-btn-primary" :disabled="running || !file" @click="submit">
          <span v-if="running" class="rw-spinner"></span>
          {{ running ? 'Analizando…' : 'Analizar' }}
        </button>
      </section>

      <!-- Ingest regulations -->
      <section class="rw-card rw-ingest" :class="{ 'rw-ingest-complete': ingestDone }">
        <div class="rw-ingest-header">
          <div>
            <p class="rw-field-label">Base de regulaciones</p>
            <p class="rw-ingest-sub">Ingesta GDPR, MiFID II, 4/5/6AMLD en el vector store</p>
          </div>
          <button class="rw-btn-ingest" :disabled="ingesting" @click="runIngest">
            <span v-if="ingesting" class="rw-spinner"></span>
            {{ ingesting ? 'Ingestando…' : ingestDone ? 'Re-ingestar' : 'Ingestar regulaciones' }}
          </button>
        </div>
        <div v-if="ingestDone" class="rw-ingest-done-banner">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 8l3.5 3.5L13 4.5"/></svg>
          {{ ingestTotal }} regulaciones ingestadas correctamente
        </div>
        <div v-if="ingesting || ingestLog.length" class="rw-progress-wrap">
          <div class="rw-progress-bar" :style="{ width: (ingesting && !ingestTotal ? '0' : ingestPct) + '%' }"
               :class="{ indeterminate: ingesting && !ingestTotal }"></div>
          <span class="rw-progress-label">
            <template v-if="ingesting && !ingestTotal">Iniciando…</template>
            <template v-else>{{ ingestProgress }}&nbsp;/&nbsp;{{ ingestTotal }}</template>
          </span>
        </div>
        <ul v-if="ingestLog.length" class="rw-ingest-log">
          <li v-for="(entry, i) in ingestLog" :key="i" :class="'rw-log-' + entry.status">
            <span class="rw-log-name">{{ entry.regulation }}</span>
            <span class="rw-log-status">{{ entry.status === 'ok' ? '✓' : entry.status === 'done' ? '✓ ' + entry.detail : '✗ ' + entry.detail }}</span>
          </li>
        </ul>
      </section>

      <!-- Pipeline rail -->
      <section class="rw-pipeline-wrap">
        <div class="rw-pipeline">
          <template v-for="(step, i) in PIPELINE" :key="step">
            <div
              class="rw-step"
              :class="{
                done: completedNodes.includes(step),
                active: isActive(step, i)
              }"
            >
              <div class="rw-step-node">
                <svg v-if="completedNodes.includes(step)" class="rw-check-icon" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M2.5 7l3 3 6-6"/>
                </svg>
                <span v-else-if="isActive(step, i)" class="rw-active-pulse"></span>
                <span v-else class="rw-step-num">{{ i + 1 }}</span>
              </div>
              <span class="rw-step-label">{{ step }}</span>
            </div>
            <div
              v-if="i < PIPELINE.length - 1"
              class="rw-connector"
              :class="{ filled: completedNodes.includes(step) }"
            ></div>
          </template>
        </div>
      </section>

      <!-- Human review alert -->
      <section v-if="needsReview" class="rw-card rw-review-alert">
        <div class="rw-review-icon">!</div>
        <div class="rw-review-body">
          <p class="rw-review-title">Revisión humana requerida</p>
          <p class="rw-review-sub">{{ needsReview.reason || 'El judge no aprobó el informe automáticamente. Revise el análisis antes de continuar.' }}</p>
          <div class="rw-review-actions">
            <button class="rw-btn-approve" @click="resume('approve')">Aprobar informe</button>
            <button class="rw-btn-reject" @click="resume('reject')">Rechazar</button>
          </div>
        </div>
      </section>

      <!-- Report -->
      <section v-if="report" class="rw-report">

        <!-- Memory diff bar -->
        <div class="rw-memory-bar">
          <div class="rw-mem-stat resolved">
            <span class="rw-mem-icon">✓</span>
            <span class="rw-mem-count">{{ report.memory_diff?.resolved.length ?? 0 }}</span>
            <span class="rw-mem-label">Resueltos</span>
          </div>
          <div class="rw-mem-divider"></div>
          <div class="rw-mem-stat open">
            <span class="rw-mem-icon">◎</span>
            <span class="rw-mem-count">{{ report.memory_diff?.still_open.length ?? 0 }}</span>
            <span class="rw-mem-label">Abiertos</span>
          </div>
          <div class="rw-mem-divider"></div>
          <div class="rw-mem-stat new-gaps">
            <span class="rw-mem-icon">+</span>
            <span class="rw-mem-count">{{ report.memory_diff?.new.length ?? 0 }}</span>
            <span class="rw-mem-label">Nuevos gaps</span>
          </div>
        </div>

        <!-- Gaps table -->
        <div class="rw-card rw-gaps-card">
          <h2 class="rw-section-title">Gaps detectados</h2>
          <div class="rw-table-wrap">
            <table class="rw-table">
              <thead>
                <tr>
                  <th>Regulación</th>
                  <th>Riesgo</th>
                  <th>Gap</th>
                  <th>Remediación</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(g, i) in report.gaps" :key="i">
                  <td class="rw-mono">{{ g.regulation_ref }}</td>
                  <td>
                    <span class="rw-risk-badge" :data-risk="g.risk_level">{{ g.risk_level }}</span>
                  </td>
                  <td>{{ g.gap_description }}</td>
                  <td class="rw-cell-remediation">{{ g.remediation }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Meta footer -->
        <div class="rw-report-meta">
          <div class="rw-meta-group">
            <span class="rw-meta-label">Tickets JIRA</span>
            <div class="rw-tickets">
              <span
                v-if="report.jira_ticket_ids?.length"
                v-for="t in report.jira_ticket_ids"
                :key="t"
                class="rw-ticket-chip"
              >{{ t }}</span>
              <span v-else class="rw-no-tickets">—</span>
            </div>
          </div>
          <a
            v-if="report.trace_url"
            :href="report.trace_url"
            target="_blank"
            rel="noopener"
            class="rw-trace-link"
          >
            Ver traza de auditoría en LangFuse
            <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 10L10 2M5 2h5v5"/>
            </svg>
          </a>
        </div>

        <!-- Chat -->
        <div class="rw-card rw-chat">
          <h2 class="rw-section-title">Preguntas sobre el informe</h2>
          <div class="rw-chat-history" ref="chatEl">
            <div
              v-for="(msg, i) in chatHistory"
              :key="i"
              class="rw-chat-msg"
              :class="msg.role"
            >
              <span class="rw-chat-role">{{ msg.role === 'user' ? 'Tú' : 'RegWatch' }}</span>
              <p class="rw-chat-text">{{ msg.text }}</p>
            </div>
            <div v-if="chatLoading" class="rw-chat-msg assistant rw-chat-loading">
              <span class="rw-chat-role">RegWatch</span>
              <span class="rw-spinner rw-spinner-dark"></span>
            </div>
          </div>
          <div class="rw-chat-input-row">
            <input
              class="rw-input rw-chat-input"
              v-model="chatInput"
              placeholder="Pregunta sobre los gaps o las regulaciones…"
              :disabled="chatLoading"
              @keydown.enter="sendChat"
            />
            <button class="rw-btn-primary" :disabled="chatLoading || !chatInput.trim()" @click="sendChat">Enviar</button>
          </div>
        </div>

      </section>
    </main>
  </div>
</template>

<style scoped>
/* ── App shell ─────────────────────────────────────────── */
.rw-app {
  display: flex;
  height: 100vh;
  background: var(--bg);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

/* ── Sidebar ───────────────────────────────────────────── */
.rw-sidebar {
  width: 210px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  overflow-y: auto;
}

.rw-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rw-brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-family: 'Palatino Linotype', Palatino, Georgia, serif;
  font-size: 13px;
  font-weight: 700;
  display: grid;
  place-items: center;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.rw-brand-name {
  font-family: 'Palatino Linotype', Palatino, Georgia, serif;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.rw-brand-sub {
  font-size: 11px;
  color: var(--text-secondary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.rw-sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rw-sidebar-label {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.rw-sidebar-pipeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rw-sidebar-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 3px 0;
  transition: color 0.25s;
}

.rw-sidebar-step.done {
  color: var(--done);
}

.rw-sidebar-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
  transition: background 0.25s;
}

.rw-sidebar-step.done .rw-sidebar-dot {
  background: var(--done);
}

.rw-sidebar-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rw-progress-label {
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.rw-progress-track {
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.rw-progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* ── Main ──────────────────────────────────────────────── */
.rw-main {
  flex: 1;
  overflow-y: auto;
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  min-width: 0;
}

/* ── Header ────────────────────────────────────────────── */
.rw-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}

.rw-eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.rw-title {
  margin: 0;
  font-family: 'Palatino Linotype', Palatino, Georgia, serif;
  font-size: 26px;
  font-weight: 400;
  color: var(--text-primary);
  line-height: 1.2;
  text-wrap: balance;
}

.rw-running-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 25%, transparent);
  border-radius: 20px;
  padding: 5px 12px;
  white-space: nowrap;
}

.rw-btn-stop {
  margin-left: 6px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
  background: color-mix(in srgb, var(--risk-high) 15%, transparent);
  color: var(--risk-high);
  border: 1px solid color-mix(in srgb, var(--risk-high) 35%, transparent);
  border-radius: 12px;
  transition: background 0.15s;
}
.rw-btn-stop:hover {
  background: color-mix(in srgb, var(--risk-high) 28%, transparent);
}

.rw-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

/* ── Card base ─────────────────────────────────────────── */
.rw-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem 2rem;
}

/* ── Upload ────────────────────────────────────────────── */
.rw-upload {
  display: flex;
  align-items: flex-end;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.rw-upload-fields {
  display: flex;
  gap: 1.25rem;
  flex: 1;
  flex-wrap: wrap;
}

.rw-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rw-field-label {
  font-size: 11px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.rw-input {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-primary);
  font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  padding: 9px 12px;
  outline: none;
  transition: border-color 0.2s;
  width: 160px;
}

.rw-input:focus {
  border-color: var(--accent);
}

.rw-file-drop {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border: 1px dashed var(--border);
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  transition: border-color 0.2s, color 0.2s;
  white-space: nowrap;
}

.rw-file-drop input[type="file"] {
  display: none;
}

.rw-file-drop:hover,
.rw-file-drop.has-file {
  border-color: var(--accent);
  color: var(--text-primary);
}

.rw-file-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.rw-btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
  font-family: inherit;
}

.rw-btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.rw-btn-primary:not(:disabled):hover {
  opacity: 0.88;
}

.rw-spinner {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  animation: spin 0.65s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Ingest section ─────────────────────────────────────────────── */
.rw-ingest {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rw-ingest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.rw-ingest-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.rw-btn-ingest {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s, border-color 0.2s;
  font-family: inherit;
}

.rw-btn-ingest:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.rw-btn-ingest:not(:disabled):hover {
  background: var(--surface-3, #2a2a3a);
  border-color: var(--accent);
}

.rw-btn-ingest .rw-spinner {
  border-color: rgba(255,255,255,0.2);
  border-top-color: var(--accent);
}

.rw-ingest-log {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rw-ingest-log li {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--surface-2);
}

.rw-log-ok   { border-left: 3px solid #4ade80; }
.rw-log-done { border-left: 3px solid #60a5fa; }
.rw-log-error { border-left: 3px solid #f87171; }

.rw-log-name   { color: var(--text); font-weight: 500; }
.rw-log-status { color: var(--text-muted); }

.rw-ingest-complete {
  border-color: #4ade8066;
}

.rw-ingest-done-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #4ade8015;
  border: 1px solid #4ade8044;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #4ade80;
}

.rw-ingest-done-banner svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  stroke: #4ade80;
}

/* ── Progress bar ───────────────────────────────────────────────── */
.rw-progress-wrap {
  position: relative;
  height: 6px;
  background: var(--surface-2);
  border-radius: 99px;
  overflow: hidden;
  display: flex;
  align-items: center;
}

.rw-progress-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.4s ease;
  min-width: 0;
}

.rw-progress-bar.indeterminate {
  width: 30% !important;
  animation: indeterminate 1.4s ease-in-out infinite;
}

@keyframes indeterminate {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

.rw-progress-label {
  position: absolute;
  right: 0;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1;
  top: -16px;
}

/* ── Pipeline rail ─────────────────────────────────────── */
.rw-pipeline-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem 2rem;
  overflow-x: auto;
}

.rw-pipeline {
  display: flex;
  align-items: center;
  min-width: max-content;
  gap: 0;
}

.rw-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.rw-step-node {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 2px solid var(--border);
  background: var(--bg);
  display: grid;
  place-items: center;
  transition: border-color 0.3s, background 0.3s;
  flex-shrink: 0;
}

.rw-step.done .rw-step-node {
  border-color: var(--done);
  background: color-mix(in srgb, var(--done) 12%, transparent);
  color: var(--done);
}

.rw-step.active .rw-step-node {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.rw-check-icon {
  width: 14px;
  height: 14px;
  stroke: var(--done);
}

.rw-step-num {
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.rw-active-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1s ease-in-out infinite;
}

.rw-step-label {
  font-size: 10.5px;
  color: var(--text-secondary);
  text-align: center;
  white-space: nowrap;
  transition: color 0.25s;
  max-width: 70px;
  line-height: 1.3;
}

.rw-step.done .rw-step-label {
  color: var(--done);
}

.rw-step.active .rw-step-label {
  color: var(--accent);
}

.rw-connector {
  flex: 1;
  height: 2px;
  background: var(--border);
  min-width: 20px;
  margin-bottom: 22px;
  transition: background 0.4s ease;
}

.rw-connector.filled {
  background: var(--done);
}

/* ── Review alert ──────────────────────────────────────── */
.rw-review-alert {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
  border-color: color-mix(in srgb, var(--risk-medium) 40%, transparent);
  background: color-mix(in srgb, var(--risk-medium) 6%, var(--surface));
}

.rw-review-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--risk-medium) 20%, transparent);
  border: 1px solid color-mix(in srgb, var(--risk-medium) 40%, transparent);
  color: var(--risk-medium);
  font-size: 18px;
  font-weight: 700;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.rw-review-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rw-review-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--risk-medium);
}

.rw-review-sub {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.rw-review-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 4px;
}

.rw-btn-approve {
  background: color-mix(in srgb, var(--done) 15%, transparent);
  color: var(--done);
  border: 1px solid color-mix(in srgb, var(--done) 35%, transparent);
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s;
}

.rw-btn-approve:hover {
  background: color-mix(in srgb, var(--done) 25%, transparent);
}

.rw-btn-reject {
  background: color-mix(in srgb, var(--risk-high) 12%, transparent);
  color: var(--risk-high);
  border: 1px solid color-mix(in srgb, var(--risk-high) 30%, transparent);
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s;
}

.rw-btn-reject:hover {
  background: color-mix(in srgb, var(--risk-high) 22%, transparent);
}

/* ── Report ────────────────────────────────────────────── */
.rw-report {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Memory bar */
.rw-memory-bar {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

.rw-mem-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 1rem 1.5rem;
  flex: 1;
}

.rw-mem-divider {
  width: 1px;
  height: 36px;
  background: var(--border);
  flex-shrink: 0;
}

.rw-mem-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.rw-mem-count {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.rw-mem-label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.rw-mem-stat.resolved .rw-mem-icon,
.rw-mem-stat.resolved .rw-mem-count { color: var(--done); }

.rw-mem-stat.open .rw-mem-icon,
.rw-mem-stat.open .rw-mem-count { color: var(--risk-medium); }

.rw-mem-stat.new-gaps .rw-mem-icon,
.rw-mem-stat.new-gaps .rw-mem-count { color: var(--risk-high); }

/* Gaps card */
.rw-gaps-card {
  padding: 0;
  overflow: hidden;
}

.rw-section-title {
  margin: 0;
  padding: 1.25rem 2rem 1rem;
  font-family: 'Palatino Linotype', Palatino, Georgia, serif;
  font-size: 17px;
  font-weight: 400;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border);
}

.rw-table-wrap {
  overflow-x: auto;
}

.rw-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
}

.rw-table thead th {
  padding: 10px 16px;
  text-align: left;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--border) 30%, var(--surface));
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.rw-table tbody td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
  vertical-align: top;
  line-height: 1.5;
}

.rw-table tbody tr:last-child td {
  border-bottom: none;
}

.rw-table tbody tr:hover td {
  background: color-mix(in srgb, var(--accent) 4%, transparent);
}

.rw-mono {
  font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
  font-size: 12.5px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.rw-cell-remediation {
  max-width: 320px;
}

/* Risk badges */
.rw-risk-badge {
  display: inline-block;
  padding: 3px 9px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}

.rw-risk-badge[data-risk="HIGH"] {
  background: color-mix(in srgb, var(--risk-high) 14%, transparent);
  color: var(--risk-high);
  border: 1px solid color-mix(in srgb, var(--risk-high) 30%, transparent);
}

.rw-risk-badge[data-risk="MEDIUM"] {
  background: color-mix(in srgb, var(--risk-medium) 14%, transparent);
  color: var(--risk-medium);
  border: 1px solid color-mix(in srgb, var(--risk-medium) 30%, transparent);
}

.rw-risk-badge[data-risk="LOW"] {
  background: color-mix(in srgb, var(--risk-low) 14%, transparent);
  color: var(--risk-low);
  border: 1px solid color-mix(in srgb, var(--risk-low) 30%, transparent);
}

/* Report meta footer */
.rw-report-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem 1.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.rw-meta-group {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  flex: 1;
}

.rw-meta-label {
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  white-space: nowrap;
}

.rw-tickets {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rw-ticket-chip {
  display: inline-block;
  padding: 3px 9px;
  background: var(--accent-dim);
  color: color-mix(in srgb, var(--accent) 80%, var(--text-primary));
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  border-radius: 4px;
  font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
  font-size: 12px;
}

.rw-no-tickets {
  color: var(--text-secondary);
  font-size: 13px;
}

.rw-trace-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--accent);
  text-decoration: none;
  font-size: 12.5px;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.rw-trace-link:hover {
  opacity: 0.75;
}

.rw-trace-link svg {
  width: 11px;
  height: 11px;
}

/* ── Focus / accessibility ─────────────────────────────── */
.rw-btn-primary:focus-visible,
.rw-btn-approve:focus-visible,
.rw-btn-reject:focus-visible,
.rw-trace-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.rw-input:focus-visible {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent);
}

/* ── Chat ──────────────────────────────────────────────── */
.rw-chat {
  padding: 0;
  overflow: hidden;
}

.rw-chat-history {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem 2rem;
  min-height: 60px;
  max-height: 340px;
  overflow-y: auto;
}

.rw-chat-msg {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.rw-chat-role {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.rw-chat-msg.user .rw-chat-role { color: var(--accent); }

.rw-chat-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.rw-chat-loading {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.rw-spinner-dark {
  border-color: var(--border);
  border-top-color: var(--accent);
}

.rw-chat-input-row {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 2rem 1.25rem;
  border-top: 1px solid var(--border);
}

.rw-chat-input {
  flex: 1;
  width: auto;
}

/* ── Reduced motion ────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .rw-spinner, .rw-pulse, .rw-active-pulse { animation: none; }
  .rw-connector, .rw-step-node, .rw-progress-fill { transition: none; }
}
</style>
