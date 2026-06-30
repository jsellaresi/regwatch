<script setup>
import { ref } from 'vue'

const props = defineProps({
  report:      { type: Object, required: true },
  chatHistory: { type: Array,  default: () => [] },
  chatLoading: { type: Boolean, default: false },
})
const emit = defineEmits(['chat'])

const chatInput = ref('')

function sendChat() {
  const q = chatInput.value.trim()
  if (!q || props.chatLoading) return
  chatInput.value = ''
  emit('chat', q)
}
</script>

<template>
  <section class="rw-report">

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
              <td><span class="rw-risk-badge" :data-risk="g.risk_level">{{ g.risk_level }}</span></td>
              <td>{{ g.gap_description }}</td>
              <td class="rw-cell-remediation">{{ g.remediation }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Meta footer -->
    <div class="rw-card rw-report-meta">
      <div class="rw-meta-group">
        <span class="rw-meta-label">Tickets JIRA</span>
        <div class="rw-tickets">
          <!-- v-if and v-for on the same element is a Vue anti-pattern; use <template> to separate them -->
          <template v-if="report.jira_ticket_ids?.length">
            <span v-for="t in report.jira_ticket_ids" :key="t" class="rw-ticket-chip">{{ t }}</span>
          </template>
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
      <div class="rw-chat-history">
        <div v-for="(msg, i) in chatHistory" :key="i" class="rw-chat-msg" :class="msg.role">
          <span class="rw-chat-role">{{ msg.role === 'user' ? 'Tú' : 'RegWatch' }}</span>
          <p class="rw-chat-text">{{ msg.text }}</p>
        </div>
        <div v-if="chatLoading" class="rw-chat-msg assistant rw-chat-loading">
          <span class="rw-chat-role">RegWatch</span>
          <span class="rw-spinner rw-spinner--chat"></span>
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
        <button class="rw-btn-primary" :disabled="chatLoading || !chatInput.trim()" @click="sendChat">
          Enviar
        </button>
      </div>
    </div>

  </section>
</template>

<style lang="scss" scoped>
@use '../assets/mixins' as *;
.rw-report { display: flex; flex-direction: column; gap: 1.25rem; }

/* ── Memory bar ── */
.rw-memory-bar {
  display: flex;
  align-items: center;
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

  &.resolved .rw-mem-icon,
  &.resolved .rw-mem-count { color: var(--done); }

  &.open .rw-mem-icon,
  &.open .rw-mem-count { color: var(--risk-medium); }

  &.new-gaps .rw-mem-icon,
  &.new-gaps .rw-mem-count { color: var(--risk-high); }
}

/* ── Gaps table ── */
.rw-gaps-card { padding: 0; overflow: hidden; }

.rw-table-wrap { overflow-x: auto; }

.rw-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;

  thead th {
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

  tbody {
    td {
      padding: 11px 16px;
      border-bottom: 1px solid var(--border);
      color: var(--text-primary);
      vertical-align: top;
      line-height: 1.5;
    }

    tr:last-child td { border-bottom: none; }

    tr:hover td { background: color-mix(in srgb, var(--accent) 4%, transparent); }
  }
}

.rw-cell-remediation { max-width: 320px; }

/* ── Risk badges ── */
.rw-risk-badge {
  display: inline-block;
  padding: 3px 9px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;

  &[data-risk='HIGH'] {
    background: color-mix(in srgb, var(--risk-high) 14%, transparent);
    color: var(--risk-high);
    border: 1px solid color-mix(in srgb, var(--risk-high) 30%, transparent);
  }

  &[data-risk='MEDIUM'] {
    background: color-mix(in srgb, var(--risk-medium) 14%, transparent);
    color: var(--risk-medium);
    border: 1px solid color-mix(in srgb, var(--risk-medium) 30%, transparent);
  }

  &[data-risk='LOW'] {
    background: color-mix(in srgb, var(--risk-low) 14%, transparent);
    color: var(--risk-low);
    border: 1px solid color-mix(in srgb, var(--risk-low) 30%, transparent);
  }
}

/* ── Report meta footer ── */
.rw-report-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem 1.5rem;
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

.rw-tickets      { display: flex; gap: 6px; flex-wrap: wrap; }
.rw-no-tickets   { color: var(--text-secondary); font-size: 13px; }

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

.rw-trace-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--accent);
  text-decoration: none;
  font-size: 12.5px;
  white-space: nowrap;
  transition: opacity 0.2s;

  &:hover         { opacity: 0.75; }
  &:focus-visible { @include focus-ring; }
  svg             { width: 11px; height: 11px; }
}

/* ── Chat ── */
.rw-chat { padding: 0; overflow: hidden; }

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

  &.user .rw-chat-role { color: var(--accent); }

  &.rw-chat-loading { flex-direction: row; align-items: center; gap: 10px; }
}

.rw-chat-role {
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.rw-chat-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.55;
  color: var(--text-primary);
  white-space: pre-wrap;
}

/* Dark-background spinner variant for chat */
.rw-spinner--chat {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  animation: rw-spin 0.65s linear infinite;
  flex-shrink: 0;
}

@keyframes rw-spin { to { transform: rotate(360deg); } }

.rw-chat-input-row {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 2rem 1.25rem;
  border-top: 1px solid var(--border);
}

.rw-chat-input { flex: 1; width: auto; }

@media (prefers-reduced-motion: reduce) {
  .rw-spinner--chat { animation: none; }
}
</style>
