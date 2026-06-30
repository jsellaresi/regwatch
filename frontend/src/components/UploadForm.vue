<script setup>
import { ref } from 'vue'

const props = defineProps({
  running: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const policyId = ref('policy-001')
const file = ref(null)

function onFile(e) { file.value = e.target.files[0] }
function submit() {
  if (file.value) emit('submit', file.value, policyId.value)
}
</script>

<template>
  <section class="rw-card rw-upload">
    <div class="rw-upload-fields">
      <div class="rw-field">
        <label class="rw-field-label" for="policy-id">Policy ID</label>
        <input id="policy-id" class="rw-input" v-model="policyId" placeholder="policy-001" />
      </div>

      <div class="rw-field">
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
</template>

<style lang="scss" scoped>
.rw-upload {
  display: flex;
  align-items: flex-end;
  gap: 1.25rem;
  flex-wrap: wrap;

  &-fields {
    display: flex;
    gap: 1.25rem;
    flex: 1;
    flex-wrap: wrap;
  }
}

.rw-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
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

  input[type='file'] { display: none; }

  &:hover,
  &.has-file {
    border-color: var(--accent);
    color: var(--text-primary);
  }
}

.rw-file-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
</style>
