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

const PRE_HITL_LABELS = ['Cache','Extracción','Guardrail entrada','Retrieval','Reranking',
  'Tools','Análisis','Guardrail salida','Judge','Revisión humana']
const ALL_LABELS = [...new Set(Object.values(NODE_LABELS))]

export function useAnalysis() {
  const completedNodes = ref([])
  const report = ref(null)
  const needsReview = ref(null)
  const running = ref(false)
  const threadId = ref(null)
  const chatHistory = ref([])
  const chatLoading = ref(false)
  let _abort = null

  // Add labels without duplicates
  function _addNodes(labels) {
    for (const l of labels) if (!completedNodes.value.includes(l)) completedNodes.value.push(l)
  }

  // Apply a /state response.
  // Returns: true = terminal state applied, null = aborted/dead, false = still running
  function _applyState(data) {
    if (!data || data.status === 'aborted') return null
    if (data.status === 'completed')    { report.value = data;      _addNodes(ALL_LABELS);      return true }
    if (data.status === 'needs_review') { needsReview.value = data; _addNodes(PRE_HITL_LABELS); return true }
    return false
  }

  async function _fetchState(tid) {
    try { return await (await fetch(`/state/${encodeURIComponent(tid)}`)).json() } catch { return null }
  }

  function cancel() {
    running.value = false
    _abort?.abort(); _abort = null
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
    // Append a run timestamp so each fresh analysis gets its own LangGraph thread.
    // Reusing the same thread_id on a HITL-paused thread returns an empty stream.
    threadId.value = `${policyId}:${file.name}:${Date.now()}`
    sessionStorage.setItem('rw_thread_id', threadId.value)

    const form = new FormData()
    form.append('file', file)
    form.append('policy_id', policyId)
    form.append('thread_id', threadId.value)

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
          if (ev === 'node')         _addNodes([NODE_LABELS[data.node] || data.node])
          if (ev === 'needs_review') needsReview.value = data
          if (ev === 'done')         report.value = data
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.error('analyze stream error', e)
    }
    _abort = null
    running.value = false

    // Fallback: SSE closed before a terminal event arrived (e.g. ERR_ABORTED on proxy)
    if (!report.value && !needsReview.value) _applyState(await _fetchState(threadId.value))
  }

  async function resume(decision) {
    needsReview.value = null
    running.value = true
    const form = new FormData()
    form.append('thread_id', threadId.value)
    form.append('decision', decision)
    const data = await (await fetch('/resume', { method: 'POST', body: form })).json()
    if (data.status === 'done') {
      report.value = data.final_report
      // resume returns JSON, not a stream — mark post-HITL steps done manually
      _addNodes(['Revisión humana', 'Informe', 'Tickets JIRA', 'Memoria'])
    } else if (data.status === 'needs_review') {
      needsReview.value = data
    }
    running.value = false
  }

  async function restoreSession() {
    const saved = sessionStorage.getItem('rw_thread_id')
    if (!saved) return
    threadId.value = saved
    const result = _applyState(await _fetchState(saved))
    if (result === null) {
      // Aborted / dead thread — clear session
      sessionStorage.removeItem('rw_thread_id')
      threadId.value = null
    } else if (result === false) {
      // Still running — poll until done
      running.value = true
      _pollUntilDone(saved)
    }
    // result === true: terminal state already applied, nothing else to do
  }

  async function _pollUntilDone(tid) {
    const MAX_POLLS = 45  // ~90 s at 2 s interval
    for (let i = 0; i < MAX_POLLS && running.value; i++) {
      await new Promise(r => setTimeout(r, 2000))
      const result = _applyState(await _fetchState(tid))
      if (result !== false) break  // terminal (true) or aborted/dead (null)
    }
    running.value = false
    if (!report.value && !needsReview.value) {
      // Timed out or aborted — clean up session
      sessionStorage.removeItem('rw_thread_id')
      threadId.value = null
    }
  }

  async function chat(question) {
    chatHistory.value.push({ role: 'user', text: question })
    chatLoading.value = true
    const form = new FormData()
    form.append('thread_id', threadId.value)
    form.append('question', question)
    const { answer } = await (await fetch('/chat', { method: 'POST', body: form })).json()
    chatHistory.value.push({ role: 'assistant', text: answer })
    chatLoading.value = false
  }

  return {
    completedNodes, report, needsReview, running,
    threadId, chatHistory, chatLoading,
    analyze, resume, chat, restoreSession, cancel, NODE_LABELS,
  }
}
