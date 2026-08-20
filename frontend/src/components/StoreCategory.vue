<template>
  <div ref="el" class="chart"></div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useEChart } from '../composables/useEChart'
import { INK, STORE_CATEGORY_COLOR } from '../theme'
import { fmtMoney } from '../theme'
import type { StoreCategory } from '../types'

const props = defineProps<{ data: StoreCategory[] }>()
const el = ref<HTMLDivElement>()

const option = () => {
  const rows = [...props.data].reverse()
  return {
    grid: { left: 8, right: 64, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#fff',
      borderColor: INK.gridline,
      textStyle: { color: INK.primary, fontSize: 12 },
      formatter: (ps: any) => {
        const d = rows[ps[0].dataIndex]
        return `${d.category}门店<br/>营业额 <b>${fmtMoney(d.revenue)}</b><br/>订单 ${d.order_count}`
      },
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: INK.gridline, width: 1 } },
      axisLabel: { color: INK.muted, fontSize: 11, formatter: (v: number) => (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v) },
    },
    yAxis: {
      type: 'category',
      data: rows.map((d) => d.category),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: INK.secondary, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((d) => ({
          value: d.revenue,
          itemStyle: { color: STORE_CATEGORY_COLOR[d.category] || INK.baseline },
        })),
        barWidth: 16,
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: INK.secondary, fontSize: 11, formatter: (p: any) => fmtMoney(p.value) },
      },
    ],
  }
}

useEChart(el, option, () => props.data)
</script>
