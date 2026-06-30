<script setup>
defineProps({ reason: String })
defineEmits(['approve', 'reject'])
</script>

<template>
  <section class="rw-card rw-review-alert">
    <div class="rw-review-icon">!</div>
    <div class="rw-review-body">
      <p class="rw-review-title">Revisión humana requerida</p>
      <p class="rw-review-sub">
        {{ reason || 'El judge no aprobó el informe automáticamente. Revise el análisis antes de continuar.' }}
      </p>
      <div class="rw-review-actions">
        <button class="rw-btn-approve" @click="$emit('approve')">Aprobar informe</button>
        <button class="rw-btn-reject"  @click="$emit('reject')">Rechazar</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
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

.rw-review-body { display: flex; flex-direction: column; gap: 6px; }

.rw-review-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--risk-medium); }
.rw-review-sub   { margin: 0; font-size: 13px; color: var(--text-secondary); }

.rw-review-actions { display: flex; gap: 0.75rem; margin-top: 4px; }

.rw-btn-approve,
.rw-btn-reject {
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s;
}

.rw-btn-approve {
  background: color-mix(in srgb, var(--done) 15%, transparent);
  color: var(--done);
  border: 1px solid color-mix(in srgb, var(--done) 35%, transparent);
}
.rw-btn-approve:hover { background: color-mix(in srgb, var(--done) 25%, transparent); }

.rw-btn-reject {
  background: color-mix(in srgb, var(--risk-high) 12%, transparent);
  color: var(--risk-high);
  border: 1px solid color-mix(in srgb, var(--risk-high) 30%, transparent);
}
.rw-btn-reject:hover { background: color-mix(in srgb, var(--risk-high) 22%, transparent); }

.rw-btn-approve:focus-visible,
.rw-btn-reject:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
