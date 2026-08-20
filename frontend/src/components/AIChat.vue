<template>
  <div class="card chat">
    <h3>AI 数据问答</h3>

    <div class="messages">
      <div v-if="messages.length === 0" class="hint">
        <span>试试问我：</span>
        <button v-for="q in suggestions" :key="q" class="suggest" @click="ask(q)">{{ q }}</button>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble">
          <div class="content">{{ m.content }}</div>
          <template v-if="m.role === 'assistant' && m.evidence">
            <div class="evidence-toggle" @click="toggleEvidence(i)">
              <span class="check">✓</span> 数据依据
              <span class="arrow">{{ showEvidence[i] ? '▾' : '▸' }}</span>
            </div>
            <div v-if="showEvidence[i]" class="evidence">
              <div class="row"><span>统计口径</span><span>{{ m.evidence.metric }}</span></div>
              <div class="row"><span>时间范围</span><span>{{ m.evidence.period }}</span></div>
              <div class="row"><span>匹配记录</span><span>{{ m.evidence.record_count }} 条</span></div>
              <div class="row"><span>数据来源</span><span>{{ m.evidence.tool_label }}</span></div>
            </div>
          </template>
          <MiniChart v-if="m.role === 'assistant'" :tool="m.tool_used" :data="m.data" />
        </div>
      </div>

      <div v-if="loading" class="msg assistant">
        <div class="bubble typing">正在查询真实数据…</div>
      </div>
    </div>

    <div class="input-row">
      <el-input v-model="input" placeholder="例如：牛肉poke 六月卖了多少钱？" @keyup.enter="send" />
      <el-button type="primary" :disabled="loading || !input.trim()" @click="send">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { postChat } from '../api'
import type { ChatMessage } from '../types'
import MiniChart from './MiniChart.vue'

const suggestions = ['哪个品类的门店营业额最高？', '牛肉poke 六月卖了多少钱？', '客单价最近是涨了还是跌了？']

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const showEvidence = ref<Record<number, boolean>>({})

// 会话 id：用于对话上下文（「那五月呢？」）
const conversationId = 'c' + Math.random().toString(36).slice(2, 10)

function toggleEvidence(i: number) {
  showEvidence.value[i] = !showEvidence.value[i]
}

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  messages.value.push({ role: 'user', content: q })
  input.value = ''
  loading.value = true
  try {
    const res = await postChat(q, conversationId)
    messages.value.push({
      role: 'assistant',
      content: res.answer,
      data: res.data,
      evidence: res.evidence,
      tool_used: res.tool_used,
    })
  } catch {
    messages.value.push({ role: 'assistant', content: '请求失败：请确认后端已启动，并在 backend/.env 配置 DEEPSEEK_API_KEY。' })
  } finally {
    loading.value = false
  }
}

function ask(q: string) {
  input.value = q
  send()
}
</script>

<style scoped>
.chat {
  margin-top: 18px;
}
.messages {
  min-height: 120px;
  max-height: 520px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}
.hint {
  font-size: 13px;
  color: var(--ink-secondary);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.suggest {
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--ink-secondary);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.suggest:hover {
  border-color: var(--blue);
  color: var(--blue);
}
.msg {
  display: flex;
}
.msg.user {
  justify-content: flex-end;
}
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
}
.msg.user .bubble {
  background: var(--blue);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg.assistant .bubble {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}
.typing {
  color: var(--ink-muted);
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
}
.evidence-toggle {
  margin-top: 8px;
  font-size: 12px;
  color: var(--blue);
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 4px;
}
.evidence-toggle .check {
  color: var(--good);
  font-weight: 700;
}
.evidence {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--page);
  border-radius: 8px;
  font-size: 12px;
}
.evidence .row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 3px 0;
  color: var(--ink-secondary);
}
.evidence .row span:last-child {
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.input-row {
  display: flex;
  gap: 10px;
}
</style>
