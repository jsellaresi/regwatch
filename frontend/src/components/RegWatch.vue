<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useAnalysis, NODE_LABELS } from '../composables/useAnalysis'
import { apiKey } from '../composables/apiFetch'
import ApiKeyForm   from './ApiKeyForm.vue'
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

// During HITL, surface the gap report from the interrupt payload so the user
// can actually read what they are approving or rejecting.
const activeReport = computed(() => {
  if (report.value) return report.value
  if (needsReview.value?.gap_report) {
    return {
      gaps:         needsReview.value.gap_report.gaps ?? [],
      judge_scores: needsReview.value.judge_scores   ?? {},
      memory_diff:  null,
      trace_url:    needsReview.value.trace_url       ?? '',
      status:       'pending_review',
    }
  }
  return null
})

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

      <ApiKeyForm    v-if="!apiKey" />
      <UploadForm    :running="running" @submit="(f, pid) => analyze(f, pid)" />
      <IngestSection />
      <PipelineRail  :pipeline="PIPELINE" :completed-nodes="completedNodes" :running="running" />
      <HumanReview   v-if="needsReview" :reason="needsReview.reason" :iteration="needsReview.iteration" @approve="resume('approve')" @reject="resume('reject')" />
      <ReportSection v-if="activeReport" :report="activeReport" :chat-history="chatHistory" :chat-loading="chatLoading" @chat="chat" />
    </main>
  </div>
</template>

<style lang="scss" scoped>
@use '../assets/mixins' as *;

// ── App shell ──
.rw-app {
  display: flex;
  height: 100vh;
  background: var(--bg);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

// ── Sidebar ──
.rw-brand {
  display: flex;
  align-items: center;
  gap: 10px;

  &-mark {
    @include serif-font;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: var(--accent);
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    display: grid;
    place-items: center;
    letter-spacing: 0.02em;
    flex-shrink: 0;
  }

  &-name {
    @include serif-font;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.2;
  }

  &-sub {
    font-size: 11px;
    color: var(--text-secondary);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
}

.rw-sidebar {
  width: 210px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  overflow-y: auto;

  &-section { display: flex; flex-direction: column; gap: 0.75rem; }

  &-label { @include uppercase-label(10px, 0.1em); }

  &-pipeline {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  &-step {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
    padding: 3px 0;
    transition: color 0.25s;

    &.done {
      color: var(--done);

      .rw-sidebar-dot { background: var(--done); }
    }
  }

  &-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--border);
    flex-shrink: 0;
    transition: background 0.25s;
  }
}

// ── Main ──
.rw-main {
  flex: 1;
  overflow-y: auto;
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  min-width: 0;

  // The column scrolls; without this the pipeline card (overflow-x: auto) gets squashed
  // into its own scroll box when the window is short, instead of the page scrolling.
  > * { flex-shrink: 0; }
}

// ── Header ──
.rw-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
}

.rw-eyebrow {
  @include uppercase-label(11px, 0.1em);
  margin: 0 0 4px;
}

.rw-title {
  @include serif-font;
  margin: 0;
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

  &:hover { background: color-mix(in srgb, var(--risk-high) 28%, transparent); }
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
  50%       { opacity: 0.4; transform: scale(0.7); }
}

@media (prefers-reduced-motion: reduce) {
  .rw-pulse { animation: none; }
  .rw-sidebar-step, .rw-sidebar-dot { transition: none; }
}
</style>
