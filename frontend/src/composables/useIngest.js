import { ref, computed } from 'vue'

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
      const resp = await fetch('/ingest', { method: 'POST' })
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          if (!block.includes('data:')) continue
          const ev = ((block.match(/event: (.*)/) || [])[1] || '').trim()
          let data
          try { data = JSON.parse((block.match(/data: (.*)/) || [])[1] || '{}') } catch { continue }
          if (ev === 'progress') {
            ingestLog.value.push(data)
          }
          if (ev === 'done') {
            // data.total may be absent if backend omits it — fall back to progress count
            ingestTotal.value = data.total ?? ingestProgress.value
            ingestLog.value.push({ regulation: '—', status: 'done', detail: data.message })
            ingestDone.value = true
            sessionStorage.setItem('rw_ingest_done', '1')
            sessionStorage.setItem('rw_ingest_total', String(ingestTotal.value))
          }
        }
      }
    } catch (e) {
      ingestLog.value.push({ regulation: '—', status: 'error', detail: e.message })
    }

    // Fallback: stream closed without an explicit 'done' SSE event but we did receive
    // progress entries — infer completion rather than silently leaving the UI stale.
    if (!ingestDone.value && ingestLog.value.some(e => e.status === 'ok')) {
      ingestTotal.value = ingestProgress.value
      ingestDone.value = true
      sessionStorage.setItem('rw_ingest_done', '1')
      sessionStorage.setItem('rw_ingest_total', String(ingestTotal.value))
    }

    ingesting.value = false
  }

  return { ingesting, ingestLog, ingestTotal, ingestDone, ingestProgress, ingestPct, runIngest }
}
