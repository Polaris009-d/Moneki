<template>
  <div class="metric card">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string }>()
</script>

<style scoped>
.metric {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.label {
  font-size: 13px;
  color: var(--ink-secondary);
}
.value {
  font-size: 30px;
  font-weight: 650;
  letter-spacing: -0.5px;
  color: var(--ink);
}
</style>
