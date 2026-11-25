import { ref } from 'vue'

const STORAGE_KEY = 'rw_api_key'

export const apiKey = ref(sessionStorage.getItem(STORAGE_KEY) || '')
export const authError = ref(false)

export function setApiKey(key) {
  apiKey.value = key.trim()
  authError.value = false
  sessionStorage.setItem(STORAGE_KEY, apiKey.value)
}

export async function apiFetch(url, options = {}) {
  const resp = await fetch(url, {
    ...options,
    headers: { ...options.headers, 'X-API-Key': apiKey.value },
  })
  if (resp.status === 401) {
    apiKey.value = ''
    authError.value = true
    sessionStorage.removeItem(STORAGE_KEY)
  }
  return resp
}
