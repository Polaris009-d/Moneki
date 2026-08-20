<template>
  <div v-if="chartable" ref="el" class="mini-chart"></div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { BLUE, CATEGORICAL, INK, fmtMoney } from '../theme'

const props = defineProps<{ tool: string | null; data: any }>()
const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const CHARTABLE = new Set(['get_daily_trend', 'get_revenue_by_store_category', 'get_store_revenue_rank', 'get_payment_breakdown'])
const chartable = computed(() => CHARTABLE.has(props.tool || ''))

function buildOption(): any {
  const { tool, data } = props
  const list = Array.isArray(data) ? data : []
  if (tool === 'get_daily_trend') {
    return {
      grid: { left: 48, right: 12, top: 12, bottom: 24 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: list.map((d: any) => d.date.slice(5)), axisLabel: { color: INK.muted, fontSize: 10 }, axisLine: { lineStyle: { color: INK.baseline } } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: INK.gridline } }, axisLabel: { color: INK.muted, fontSize: 10 } },
      series: [{ type: 'line', data: list.map((d: any) => d.revenue), lineStyle: { width: 2, color: BLUE }, itemStyle: { color: BLUE }, showSymbol: false, areaStyle: { color: BLUE, opacity: 0.1 } }],
    }
  }
  if (tool === 'get_revenue_by_store_category' || tool === 'get_store_revenue_rank') {
    const rows = [...list].reverse()
    const name = (d: any) => (tool === 'get_store_revenue_rank' ? d.store_name : d.category)
    return {
      grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: INK.gridline } }, axisLabel: { color: INK.muted, fontSize: 10 } },
      yAxis: { type: 'category', data: rows.map(name), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: INK.secondary, fontSize: 11 } },
      series: [{ type: 'bar', data: rows.map((d: any) => ({ value: d.revenue, itemStyle: { color: CATEGORICAL[rows.indexOf(d) % CATEGORICAL.length] } })), barWidth: 14, itemStyle: { borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right', color: INK.secondary, fontSize: 10, formatter: (p: any) => fmtMoney(p.value) } }],
    }
  }
  if (tool === 'get_payment_breakdown') {
    return {
      tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${fmtMoney(p.value)} (${p.percent}%)` },
      legend: { bottom: 0, textStyle: { color: INK.secondary, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
      color: CATEGORICAL,
      series: [{ type: 'pie', radius: ['45%', '70%'], data: list.map((d: any) => ({ name: d.payment, value: d.revenue })), label: { color: INK.secondary, fontSize: 11 } }],
    }
  }
  return {}
}

const onResize = () => chart?.resize()

async function sync() {
  await nextTick()
  if (!chartable.value) {
    chart?.dispose()
    chart = null
    return
  }
  if (!chart && el.value) {
    chart = echarts.init(el.value)
    window.addEventListener('resize', onResize)
  }
  chart?.setOption(buildOption(), true)
}

watch(() => [props.tool, props.data], sync, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.mini-chart {
  width: 100%;
  height: 220px;
  margin-top: 8px;
  border: 1px solid var(--border);
  border-radius: 8px;
}
</style>
