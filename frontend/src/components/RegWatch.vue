<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useAnalysis, NODE_LABELS } from '../composables/useAnalysis'
import UploadForm    from './UploadForm.vue'
import IngestSection from './IngestSection.vue'
import PipelineRail  from './PipelineRail.vue'
import HumanReview   from './HumanReview.vue'
import ReportSection from './ReportSection.vue'

const {
  completedNodes, report, needsReview, running,
  chatHistory, chatLoading,
  analyze, resume, chat, restoreSession, cancel,
} = useAnalysis()

// Deduplicate aliased labels (tools_node / collect_tool_results -> 'Tools')
const PIPELINE = [...new Set(Object.values(NODE_LABELS))]

onMounted(() => restoreSession())
onUnmounted(() => { if (running.value) cancel() })
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

      <UploadForm    :running="running" @submit="(f, pid) => analyze(f, pid)" />
      <IngestSection />
      <PipelineRail  :pipeline="PIPELINE" :completed-nodes="completedNodes" :running="running" />
      <HumanReview   v-if="needsReview" :reason="needsReview.reason" @approve="resume('approve')" @reject="resume('reject')" />
      <ReportSection v-if="report" :report="report" :chat-history="chatHistory" :chat-loading="chatLoading" @chat="chat" />
    </main>
  </div>
</template>

<style scoped>
/* ── App shell ── */
.rw-app {
  display: flex;
  height: 100vh;
  background: var(--bg);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

/* ── Sidebar ── */
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

.rw-brand { display: flex; align-items: center; gap: 10px; }

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

.rw-sidebar-section { display: flex; flex-direction: column; gap: 0.75rem; }

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
.rw-sidebar-step.done { color: var(--done); }

.rw-sidebar-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border);
  flex-shrink: 0;
  transition: background 0.25s;
}
.rw-sidebar-step.done .rw-sidebar-dot { background: var(--done); }

/* ── Main ── */
.rw-main {
  flex: 1;
  overflow-y: auto;
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  min-width: 0;
}

/* ── Header ── */
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
.rw-btn-stop:hover { background: color-mix(in srgb, var(--risk-high) 28%, transparent); }

.rw-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.7); }
}

@media (prefers-reduced-motion: reduce) {
  .rw-pulse { animation: none; }
  .rw-sidebar-step, .rw-sidebar-dot { transition: none; }
}
</style>
