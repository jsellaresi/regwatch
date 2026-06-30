<script setup>
const props = defineProps({
  pipeline: { type: Array, required: true },
  completedNodes: { type: Array, required: true },
  running: { type: Boolean, default: false },
})

function isActive(step, i) {
  if (props.completedNodes.includes(step)) return false
  if (!props.running) return false
  return props.completedNodes.length === i
}
</script>

<template>
  <section class="rw-pipeline-wrap">
    <div class="rw-pipeline">
      <template v-for="(step, i) in pipeline" :key="step">
        <div
          class="rw-step"
          :class="{ done: completedNodes.includes(step), active: isActive(step, i) }"
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
          v-if="i < pipeline.length - 1"
          class="rw-connector"
          :class="{ filled: completedNodes.includes(step) }"
        ></div>
      </template>
    </div>
  </section>
</template>

<style scoped>
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
}

.rw-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
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

.rw-check-icon { width: 14px; height: 14px; stroke: var(--done); }

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

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.7); }
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

.rw-step.done .rw-step-label   { color: var(--done); }
.rw-step.active .rw-step-label { color: var(--accent); }

.rw-connector {
  flex: 1;
  height: 2px;
  background: var(--border);
  min-width: 20px;
  margin-bottom: 22px;
  transition: background 0.4s ease;
}

.rw-connector.filled { background: var(--done); }

@media (prefers-reduced-motion: reduce) {
  .rw-active-pulse { animation: none; }
  .rw-connector, .rw-step-node { transition: none; }
}
</style>
