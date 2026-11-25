import { ref, computed } from 'vue'
import { apiFetch } from './apiFetch'

export function useIngest() {
  const ingesting = ref(false)
  const ingestLog = ref([])
  const ingestTotal = ref(Number(sessionStorage.getItem('rw_ingest_total')) || 0)
  const ingestDone = ref(sessionStorage.getItem('rw_ingest_done') === '1')

  // Count only progress entries, not the final summary 'done' entry
  const ingestProgress = computed(() => ingestLog.value.filter(e => e.status !== 'done').length)
  const ingestPct = computed(() =>
    ingestTotal.value ? Math.round(ingestProgress.value / ingestTotal.value * 100) : 0
  )

  async function runIngest() {
    ingesting.value = true
    ingestLog.value = []
    ingestTotal.value = 0
    ingestDone.value = false

    try {
      const resp = await apiFetch('/ingest', { method: 'POST' })
      if (!resp.ok) {
        ingestLog.value.push({ regulation: '—', status: 'error', detail: `Error del servidor (${resp.status})` })
        ingesting.value = false
        return
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // Helper: parse and dispatch a single SSE block
      function dispatchBlock(block) {
        if (!block.includes('data:')) return
        const ev = ((block.match(/event: (.*)/) || [])[1] || '').trim()
        let data
        try { data = JSON.parse((block.match(/data: (.*)/) || [])[1] || '{}') } catch { return }
        if (ev === 'progress') {
          ingestLog.value.push(data)
        }
        if (ev === 'done') {
          ingestTotal.value = data.total ?? ingestProgress.value
          ingestLog.value.push({ regulation: '—', status: 'done', detail: data.message })
          ingestDone.value = true
          sessionStorage.setItem('rw_ingest_done', '1')
          sessionStorage.setItem('rw_ingest_total', String(ingestTotal.value))
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        buffer = buffer.replace(/\r\n/g, '\n')  // sse_starlette 3.x uses CRLF
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          dispatchBlock(buffer.slice(0, idx))
          buffer = buffer.slice(idx + 2)
        }
      }

      // Flush decoder and process any remaining block whose trailing \n\n was split
      // across the final read chunk and the stream-closed signal.
      buffer += decoder.decode()
      if (buffer.trim()) dispatchBlock(buffer.trim())

    } catch (e) {
      ingestLog.value.push({ regulation: '—', status: 'error', detail: e.message })
    }

    // Fallback: stream closed without an explicit 'done' SSE event.
    // Trigger on ANY log entries (ok or error) so the banner always appears.
    if (!ingestDone.value && ingestLog.value.length > 0) {
      ingestTotal.value = ingestProgress.value
      ingestDone.value = true
      sessionStorage.setItem('rw_ingest_done', '1')
      sessionStorage.setItem('rw_ingest_total', String(ingestTotal.value))
    }

    ingesting.value = false
  }

  return { ingesting, ingestLog, ingestTotal, ingestDone, ingestProgress, ingestPct, runIngest }
}
