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
        if (ev === 'node') completedNodes.value.push(NODE_LABELS[data.node] || data.node)
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
    report.value = await resp.json()
    running.value = false
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
    analyze, resume, chat, NODE_LABELS,
  }
}
