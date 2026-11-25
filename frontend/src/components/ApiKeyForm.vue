<script setup>
import { ref } from 'vue'
import { authError, setApiKey } from '../composables/apiFetch'

const key = ref('')
function submit() {
  if (key.value.trim()) setApiKey(key.value)
}
</script>

<template>
  <section class="rw-card rw-apikey">
    <div class="rw-field">
      <label class="rw-field-label" for="api-key">API key</label>
      <input id="api-key" class="rw-input" type="password" autocomplete="off"
             v-model="key" placeholder="REGWATCH_API_KEY" @keyup.enter="submit" />
      <p v-if="authError" class="rw-apikey-error">Clave rechazada por la API. Inténtalo de nuevo.</p>
    </div>
    <button class="rw-btn-primary" :disabled="!key.trim()" @click="submit">Guardar</button>
  </section>
</template>

<style lang="scss" scoped>
.rw-apikey {
  display: flex;
  align-items: flex-end;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.rw-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.rw-apikey-error {
  margin: 0;
  font-size: 12px;
  color: var(--risk-high);
}
</style>
