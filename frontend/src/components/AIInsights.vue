<template>
  <div class="insights">
    <div v-for="ins in insights" :key="ins.type + ins.title" class="insight" :class="ins.severity">
      <span class="dot" :style="{ background: colorOf(ins.severity) }"></span>
      <div class="body">
        <div class="title">{{ ins.title }}</div>
        <div class="text">{{ ins.text }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { STATUS } from '../theme'
import type { Insight } from '../types'

defineProps<{ insights: Insight[] }>()

function colorOf(sev: string): string {
  if (sev === 'positive') return STATUS.good
  if (sev === 'negative') return STATUS.serious
  if (sev === 'warning') return STATUS.warning
  return '#2a78d6'
}
</script>

<style scoped>
.insights {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.insight {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
}
.dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
}
.title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-muted);
  margin-bottom: 3px;
}
.text {
  font-size: 13px;
  line-height: 1.55;
  color: var(--ink);
}
</style>
