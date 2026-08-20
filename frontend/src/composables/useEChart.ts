import { onBeforeUnmount, onMounted, watch, type Ref } from 'vue'
import * as echarts from 'echarts'

/** 初始化 ECharts 实例，管理 resize 与销毁。watchSource 变化时重绘。 */
export function useEChart(
  el: Ref<HTMLDivElement | undefined>,
  buildOption: () => any,
  watchSource: Ref<any> | (() => any) = () => undefined,
) {
  let chart: echarts.ECharts | null = null
  const onResize = () => chart?.resize()

  onMounted(() => {
    if (el.value) {
      chart = echarts.init(el.value)
      chart.setOption(buildOption())
      window.addEventListener('resize', onResize)
    }
  })

  watch(watchSource, () => chart?.setOption(buildOption(), true), { deep: true })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    chart?.dispose()
    chart = null
  })
}
