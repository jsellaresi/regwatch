<script setup>
import { ref } from 'vue'
import { useAnalysis } from '../composables/useAnalysis'

const { completedNodes, report, needsReview, running, analyze, NODE_LABELS } = useAnalysis()
const policyId = ref('policy-001')
const file = ref(null)

const PIPELINE = Object.values(NODE_LABELS)
function onFile(e) { file.value = e.target.files[0] }
function submit() { if (file.value) analyze(file.value, policyId.value) }

const RISK_COLOR = { HIGH: '#c0392b', MEDIUM: '#e67e22', LOW: '#27ae60' }
</script>

<template>
  <div class="regwatch">
    <h1>RegWatch — Análisis de Compliance</h1>

    <section class="upload">
      <input v-model="policyId" placeholder="policy_id" />
      <input type="file" accept="application/pdf" @change="onFile" />
      <button :disabled="running" @click="submit">Analizar</button>
    </section>

    <section class="pipeline">
      <span v-for="step in PIPELINE" :key="step"
            class="node" :class="{ done: completedNodes.includes(step) }">
        {{ completedNodes.includes(step) ? '✓' : '○' }} {{ step }}
      </span>
    </section>

    <section v-if="needsReview" class="review">
      <p>⚠️ El judge no aprobó el informe. Revisión requerida.</p>
      <button @click="$emit('resume', 'approve')">Aprobar</button>
      <button @click="$emit('resume', 'reject')">Rechazar</button>
    </section>

    <section v-if="report" class="report">
      <h2>Gaps detectados</h2>
      <table>
        <tr><th>Regulación</th><th>Riesgo</th><th>Gap</th><th>Remediación</th></tr>
        <tr v-for="(g, i) in report.gaps" :key="i">
          <td>{{ g.regulation_ref }}</td>
          <td :style="{ color: RISK_COLOR[g.risk_level] }">{{ g.risk_level }}</td>
          <td>{{ g.gap_description }}</td>
          <td>{{ g.remediation }}</td>
        </tr>
      </table>

      <h3>Cambios vs. análisis previo (memoria episódica)</h3>
      <p>✅ Resueltos: {{ report.memory_diff?.resolved.length }} ·
         🔶 Abiertos: {{ report.memory_diff?.still_open.length }} ·
         🆕 Nuevos: {{ report.memory_diff?.new.length }}</p>

      <p>Tickets JIRA: {{ report.jira_ticket_ids?.join(', ') || '—' }}</p>
      <a :href="report.trace_url" target="_blank">Ver traza de auditoría en LangFuse →</a>
    </section>
  </div>
</template>

<style scoped>
.node { display:inline-block; margin:4px 8px; color:#999; }
.node.done { color:#27ae60; font-weight:600; }
table { border-collapse: collapse; width:100%; }
td, th { border:1px solid #ddd; padding:6px; text-align:left; font-size:14px; }
</style>
