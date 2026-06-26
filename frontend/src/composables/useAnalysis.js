import { ref } from 'vue'

const NODE_LABELS = {
  check_cache: 'Cache',
  multimodal_extract: 'Extracción',
  input_guardrail: 'Guardrail entrada',
  retrieve_regulations: 'Retrieval',
  rerank: 'Reranking',
  enrich_agent: 'Tools',
  tools_node: 'Tools',             // LangGraph ToolNode — same step as enrich_agent
  collect_tool_results: 'Tools',   // internal aggregation — same step
  analyze_compliance: 'Análisis',
  output_guardrail: 'Guardrail salida',
  agent_judge: 'Judge',
  human_review_checkpoint: 'Revisión humana',
  format_report: 'Informe',
  create_tickets: 'Tickets JIRA',
  store_episodic_memory: 'Memoria',
}

export function useAnalysis() {
  const completedNodes = ref([])
  const report = ref(null)
  const needsReview = ref(null)
  const running = ref(false)
  const threadId = ref(null)
  const chatHistory = ref([])
  const chatLoading = ref(false)
  let _abort = null   // AbortController for the active SSE fetch

  function cancel() {
    running.value = false          // stops _pollUntilDone loop
    if (_abort) { _abort.abort(); _abort = null }
    completedNodes.value = []
    report.value = null
    needsReview.value = null
    chatHistory.value = []
    sessionStorage.removeItem('rw_thread_id')
    threadId.value = null
  }

  async function analyze(file, policyId) {
    running.value = true
    completedNodes.value = []
    report.value = null
    needsReview.value = null
    chatHistory.value = []
    threadId.value = `${policyId}:${file.name}`
    sessionStorage.setItem('rw_thread_id', threadId.value)
    const form = new FormData()
    form.append('file', file)
    form.append('policy_id', policyId)

    _abort = new AbortController()
    let reader
    try {
      const resp = await fetch('/analyze/stream', { method: 'POST', body: form, signal: _abort.signal })
      reader = resp.body.getReader()
    } catch (e) {
      if (e.name !== 'AbortError') console.error('analyze fetch error', e)
      running.value = false
      return
    }
    const decoder = new TextDecoder()
    let buffer = ''
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          if (!block.includes('data:')) continue
          const ev = (block.match(/event: (.*)/) || [])[1]
          let data
          try { data = JSON.parse((block.match(/data: (.*)/) || [])[1] || '{}') } catch { continue }
          if (ev === 'node') {
            const label = NODE_LABELS[data.node] || data.node
            if (!completedNodes.value.includes(label)) completedNodes.value.push(label)
          }
          if (ev === 'needs_review') needsReview.value = data
          if (ev === 'done') report.value = data
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.error('analyze stream error', e)
    }
    _abort = null
    running.value = false
  }

  async function resume(decision) {
    const form = new FormData()
    form.append('thread_id', threadId.value)
    form.append('decision', decision)
    needsReview.value = null
    running.value = true
    const resp = await fetch('/resume', { method: 'POST', body: form })
    const data = await resp.json()
    if (data.status === 'done') {
      report.value = data.final_report
      // Mark all post-HITL steps as done — resume returns JSON, not a stream
      for (const label of ['Revisión humana', 'Informe', 'Tickets JIRA', 'Memoria']) {
        if (!completedNodes.value.includes(label)) completedNodes.value.push(label)
      }
    } else if (data.status === 'needs_review') {
      needsReview.value = data
    }
    running.value = false
  }

  async function restoreSession() {
    const saved = sessionStorage.getItem('rw_thread_id')
    if (!saved) return
    threadId.value = saved
    try {
      const resp = await fetch(`/state/${encodeURIComponent(saved)}`)
      const data = await resp.json()
      if (!data) {
        // Pipeline is still running — show spinner and poll until terminal state
        running.value = true
        _pollUntilDone(saved)
        return
      }
      if (data.status === 'completed') report.value = data
      else if (data.status === 'needs_review') needsReview.value = data
    } catch (_) {}
  }

  async function _pollUntilDone(tid) {
    while (running.value) {
      await new Promise(r => setTimeout(r, 2000))
      try {
        const resp = await fetch(`/state/${encodeURIComponent(tid)}`)
        const data = await resp.json()
        if (!data) continue          // still running, keep polling
        running.value = false
        if (data.status === 'completed') {
          report.value = data
          // All steps done
          for (const label of Object.values(NODE_LABELS)) {
            if (!completedNodes.value.includes(label)) completedNodes.value.push(label)
          }
        } else if (data.status === 'needs_review') {
          needsReview.value = data
          // Mark steps up through judge as done
          for (const label of ['Cache','Extracción','Guardrail entrada','Retrieval','Reranking','Tools','Análisis','Guardrail salida','Judge','Revisión humana']) {
            if (!completedNodes.value.includes(label)) completedNodes.value.push(label)
          }
        }
        return
      } catch (_) {}
    }
  }

  async function chat(question) {
    chatHistory.value.push({ role: 'user', text: question })
    chatLoading.value = true
    const form = new FormData()
    form.append('thread_id', threadId.value)
    form.append('question', question)
    const resp = await fetch('/chat', { method: 'POST', body: form })
    const { answer } = await resp.json()
    chatHistory.value.push({ role: 'assistant', text: answer })
    chatLoading.value = false
  }

  return {
    completedNodes, report, needsReview, running,
    threadId, chatHistory, chatLoading,
    analyze, resume, chat, restoreSession, cancel, NODE_LABELS,
  }
}
