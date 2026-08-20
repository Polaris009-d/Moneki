<template>
  <div class="dashboard">
    <header class="header">
      <div>
        <h1>Moneki Analytics</h1>
      </div>
      <el-date-picker
        v-model="range"
        type="daterange"
        value-format="YYYY-MM-DD"
        :clearable="false"
        size="large"
        :disabled-date="disabledDate"
      />
    </header>

    <section class="kpis">
      <MetricCard label="净营业额" :value="fmtMoney(summary.revenue)" />
      <MetricCard label="订单数" :value="summary.order_count.toLocaleString()" />
      <MetricCard label="客单价" :value="fmtMoney(summary.avg_order_value)" />
    </section>

    <section class="card">
      <h3>营业额趋势</h3>
      <SalesTrend :data="daily" />
    </section>

    <section class="grid-2">
      <div class="card">
        <h3>Top 10 商品</h3>
        <TopProducts :data="topProducts" />
      </div>
      <div class="card">
        <h3>门店品类营业额</h3>
        <StoreCategory :data="storeCategory" />
      </div>
    </section>

    <section class="card">
      <h3>AI 经营洞察</h3>
      <AIInsights :insights="insights" />
    </section>

    <AIChat />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchDaily, fetchInsights, fetchStoreCategory, fetchSummary, fetchTopProducts } from '../api'
import { fmtMoney } from '../theme'
import type { DailyPoint, Insight, StoreCategory as StoreCategoryRow, Summary, TopProduct } from '../types'
import AIInsights from '../components/AIInsights.vue'
import AIChat from '../components/AIChat.vue'
import MetricCard from '../components/MetricCard.vue'
import SalesTrend from '../components/SalesTrend.vue'
import StoreCategory from '../components/StoreCategory.vue'
import TopProducts from '../components/TopProducts.vue'

const range = ref<[string, string]>(['2026-05-01', '2026-07-31'])
const summary = ref<Summary>({ revenue: 0, order_count: 0, valid_order_count: 0, avg_order_value: 0 })
const daily = ref<DailyPoint[]>([])
const topProducts = ref<TopProduct[]>([])
const storeCategory = ref<StoreCategoryRow[]>([])
const insights = ref<Insight[]>([])

function disabledDate(d: Date): boolean {
  const t = d.getTime()
  const min = new Date('2026-05-01').getTime()
  const max = new Date('2026-07-31').getTime()
  return t < min || t > max
}

async function load() {
  const [s, e] = range.value
  const [sum, d, tp, sc, ins] = await Promise.all([
    fetchSummary(s, e),
    fetchDaily(s, e),
    fetchTopProducts(s, e),
    fetchStoreCategory(s, e),
    fetchInsights(s, e),
  ])
  summary.value = sum
  daily.value = d
  topProducts.value = tp
  storeCategory.value = sc
  insights.value = ins
}

onMounted(load)
watch(range, load)
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.3px;
}
.tagline {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--ink-muted);
}
.kpis {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.grid-2 {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
  margin-top: 16px;
}
.card {
  margin-bottom: 16px;
}
@media (max-width: 900px) {
  .kpis,
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
