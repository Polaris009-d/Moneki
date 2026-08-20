<template>
  <div ref="el" class="chart"></div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useEChart } from '../composables/useEChart'
import { BLUE, INK } from '../theme'
import { fmtMoney } from '../theme'
import type { DailyPoint } from '../types'

const props = defineProps<{ data: DailyPoint[] }>()
const el = ref<HTMLDivElement>()

const option = () => ({
  grid: { left: 64, right: 20, top: 24, bottom: 36 },
  tooltip: {
    trigger: 'axis',
    backgroundColor: '#fff',
    borderColor: INK.gridline,
    textStyle: { color: INK.primary, fontSize: 12 },
    formatter: (ps: any) => {
      const p = ps[0]
      const d = props.data[p.dataIndex]
      return `${p.axisValue}<br/>营业额 <b>${fmtMoney(d.revenue)}</b><br/>订单 ${d.order_count} · 客单价 ${fmtMoney(d.avg_order_value)}`
    },
  },
  xAxis: {
    type: 'category',
    data: props.data.map((d) => d.date.slice(5)),
    axisLine: { lineStyle: { color: INK.baseline } },
    axisTick: { show: false },
    axisLabel: { color: INK.muted, fontSize: 11, interval: Math.floor(props.data.length / 8) },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: INK.gridline, width: 1 } },
    axisLabel: { color: INK.muted, fontSize: 11, formatter: (v: number) => (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v) },
  },
  series: [
    {
      type: 'line',
      data: props.data.map((d) => d.revenue),
      lineStyle: { width: 2, color: BLUE },
      itemStyle: { color: BLUE },
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: false,
      areaStyle: { color: BLUE, opacity: 0.1 },
      endLabel: { show: true, color: INK.secondary, fontSize: 11, formatter: () => fmtMoney(props.data[props.data.length - 1].revenue) },
    },
  ],
})

useEChart(el, option, () => props.data)
</script>
