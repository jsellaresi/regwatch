<script setup>
import { useIngest } from '../composables/useIngest'

const { ingesting, ingestLog, ingestTotal, ingestDone, ingestProgress, ingestPct, runIngest } = useIngest()
</script>

<template>
  <section class="rw-card rw-ingest" :class="{ 'rw-ingest-complete': ingestDone }">
    <div class="rw-ingest-header">
      <div>
        <p class="rw-field-label">Base de regulaciones</p>
        <p class="rw-ingest-sub">Ingesta GDPR, MiFID II, 4/5/6AMLD en el vector store</p>
      </div>
      <button class="rw-btn-ingest" :disabled="ingesting" @click="runIngest">
        <span v-if="ingesting" class="rw-spinner rw-spinner--ingest"></span>
        {{ ingesting ? 'Ingestando…' : ingestDone ? 'Re-ingestar' : 'Ingestar regulaciones' }}
      </button>
    </div>

    <div v-if="ingestDone" class="rw-ingest-done-banner">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M3 8l3.5 3.5L13 4.5"/>
      </svg>
      {{ ingestTotal }} regulaciones ingestadas correctamente
    </div>

    <!-- Progress: count sits above the bar, not clipped inside it -->
    <template v-if="ingesting || ingestLog.length">
      <span class="rw-progress-count">
        <template v-if="ingesting && !ingestTotal">Iniciando…</template>
        <template v-else>{{ ingestProgress }}&nbsp;/&nbsp;{{ ingestTotal }}</template>
      </span>
      <div class="rw-progress-wrap">
        <div
          class="rw-progress-bar"
          :style="{ width: (ingesting && !ingestTotal ? 0 : ingestPct) + '%' }"
          :class="{ indeterminate: ingesting && !ingestTotal }"
        ></div>
      </div>
    </template>

    <ul v-if="ingestLog.length" class="rw-ingest-log">
      <li v-for="(entry, i) in ingestLog" :key="i" :class="'rw-log-' + entry.status">
        <span class="rw-log-name">{{ entry.regulation }}</span>
        <span class="rw-log-detail">
          {{ entry.status === 'ok' ? '✓' : entry.status === 'done' ? '✓ ' + entry.detail : '✗ ' + entry.detail }}
        </span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
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
  color: var(--text-secondary);
  margin-top: 2px;
}

.rw-btn-ingest {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  color: var(--text-primary);
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

.rw-btn-ingest:disabled { opacity: 0.45; cursor: not-allowed; }

.rw-btn-ingest:not(:disabled):hover {
  background: var(--border);
  border-color: var(--accent);
}

/* Override default white spinner colours for this dark button */
.rw-spinner--ingest {
  border-color: rgba(255,255,255,0.15);
  border-top-color: var(--accent);
}

/* ── Done banner ── */
.rw-ingest-complete { border-color: #4ade8066; }

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

/* ── Progress bar ── */
/* Count is rendered ABOVE the bar so it is never clipped by overflow:hidden */
.rw-progress-count {
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.rw-progress-wrap {
  height: 6px;
  background: var(--border);
  border-radius: 99px;
  overflow: hidden;
}

.rw-progress-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 99px;
  transition: width 0.4s ease;
}

.rw-progress-bar.indeterminate {
  width: 30% !important;
  animation: indeterminate 1.4s ease-in-out infinite;
}

@keyframes indeterminate {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

/* ── Log entries ── */
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
  background: color-mix(in srgb, var(--border) 60%, transparent);
}

.rw-log-ok    { border-left: 3px solid #4ade80; }
.rw-log-done  { border-left: 3px solid #60a5fa; }
.rw-log-error { border-left: 3px solid #f87171; }

.rw-log-name   { color: var(--text-primary); font-weight: 500; }
.rw-log-detail { color: var(--text-secondary); }
</style>
