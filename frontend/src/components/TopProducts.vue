<template>
  <div ref="el" class="chart"></div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useEChart } from '../composables/useEChart'
import { BLUE, INK } from '../theme'
import { fmtMoney } from '../theme'
import type { TopProduct } from '../types'

const props = defineProps<{ data: TopProduct[] }>()
const el = ref<HTMLDivElement>()

const option = () => {
  const rows = [...props.data].reverse() // ECharts 横向条形 Y 轴自下而上
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
        return `${d.product_name}（${d.product_category}）<br/>营业额 <b>${fmtMoney(d.revenue)}</b><br/>销量 ${d.qty} · 订单 ${d.order_count}`
      },
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: INK.gridline, width: 1 } },
      axisLabel: { color: INK.muted, fontSize: 11, formatter: (v: number) => (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v) },
    },
    yAxis: {
      type: 'category',
      data: rows.map((d) => d.product_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: INK.secondary, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((d) => d.revenue),
        barWidth: 16,
        itemStyle: { color: BLUE, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: INK.secondary, fontSize: 11, formatter: (p: any) => fmtMoney(p.value) },
      },
    ],
  }
}

useEChart(el, option, () => props.data)
</script>
