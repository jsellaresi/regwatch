<script setup>
defineProps({ reason: String, iteration: { type: Number, default: 1 } })
defineEmits(['approve', 'reject'])
</script>

<template>
  <section class="rw-card rw-review-alert">
    <div class="rw-review-icon">!</div>
    <div class="rw-review-body">
      <div class="rw-review-header">
        <p class="rw-review-title">Revisión humana requerida</p>
        <span v-if="iteration > 1" class="rw-review-iter">Re-análisis #{{ iteration }}</span>
      </div>
      <p class="rw-review-sub">
        {{ reason || 'El judge no aprobó el informe automáticamente. Revise el análisis antes de continuar.' }}
      </p>
      <div class="rw-review-actions">
        <button class="rw-btn-approve" @click="$emit('approve')">Aprobar informe</button>
        <button class="rw-btn-reject"  @click="$emit('reject')" title="Descarta este análisis y ejecuta uno nuevo">Rechazar y re-analizar</button>
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
@use '../assets/mixins' as *;
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

.rw-review-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rw-review-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--risk-medium); }
.rw-review-sub   { margin: 0; font-size: 13px; color: var(--text-secondary); }

.rw-review-iter {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--risk-medium) 18%, transparent);
  color: var(--risk-medium);
  border: 1px solid color-mix(in srgb, var(--risk-medium) 35%, transparent);
}

.rw-review-actions { display: flex; gap: 0.75rem; margin-top: 4px; }

@mixin btn-outline($color) {
  @include btn-outline-base;
  background: color-mix(in srgb, #{$color} 12%, transparent);
  color: #{$color};
  border: 1px solid color-mix(in srgb, #{$color} 30%, transparent);

  &:hover { background: color-mix(in srgb, #{$color} 22%, transparent); }
}

.rw-btn-approve {
  @include btn-outline(var(--done));
  background: color-mix(in srgb, var(--done) 15%, transparent);

  &:hover { background: color-mix(in srgb, var(--done) 25%, transparent); }
}

.rw-btn-reject {
  @include btn-outline(var(--risk-high));
}
</style>
