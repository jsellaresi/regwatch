import { ref } from 'vue'

const NODE_LABELS = {
  check_cache: 'Cache',
  multimodal_extract: 'Extracción',
  input_guardrail: 'Guardrail entrada',
  retrieve_regulations: 'Retrieval',
  rerank: 'Reranking',
  enrich_agent: 'Tools',
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

    const resp = await fetch('/analyze/stream', { method: 'POST', body: form })
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      for (const block of buffer.split('\n\n')) {
        if (!block.includes('data:')) continue
        const ev = (block.match(/event: (.*)/) || [])[1]
        const data = JSON.parse((block.match(/data: (.*)/) || [])[1] || '{}')
        if (ev === 'node') {
          const label = NODE_LABELS[data.node] || data.node
          if (!completedNodes.value.includes(label)) completedNodes.value.push(label)
        }
        if (ev === 'needs_review') needsReview.value = data
        if (ev === 'done') report.value = data
      }
      buffer = buffer.slice(buffer.lastIndexOf('\n\n') + 2)
    }
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
      if (data && data.status === 'completed') report.value = data
    } catch (_) {}
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
    analyze, resume, chat, restoreSession, NODE_LABELS,
  }
}
