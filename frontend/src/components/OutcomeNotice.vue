<script setup>
defineProps({ outcome: { type: Object, required: true } })
</script>

<template>
  <section class="rw-card rw-outcome" role="alert">
    <div class="rw-outcome-icon">✕</div>
    <div class="rw-outcome-body">
      <p class="rw-outcome-title">
        {{ outcome.status === 'blocked' ? 'Documento bloqueado por el guardrail de entrada' : 'El análisis terminó con un error' }}
      </p>
      <p class="rw-outcome-sub">
        {{ outcome.status === 'blocked' ? 'No se ha analizado: no se ha generado ningún informe.' : 'No se ha generado ningún informe.' }}
      </p>
      <p v-if="outcome.error" class="rw-outcome-reason">{{ outcome.error }}</p>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.rw-outcome {
  display: flex;
  align-items: flex-start;
  gap: 1.25rem;
  border-color: color-mix(in srgb, var(--risk-high) 40%, transparent);
  background: color-mix(in srgb, var(--risk-high) 6%, var(--surface));
}

.rw-outcome-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--risk-high) 20%, transparent);
  border: 1px solid color-mix(in srgb, var(--risk-high) 40%, transparent);
  color: var(--risk-high);
  font-size: 16px;
  font-weight: 700;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.rw-outcome-body { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.rw-outcome-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--risk-high); }
.rw-outcome-sub { margin: 0; font-size: 13px; color: var(--text-secondary); }
.rw-outcome-reason {
  margin: 0;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}
</style>
