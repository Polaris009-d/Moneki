// 数据可视化设计 token（来自 dataviz 校验后的默认调色板）
export const CATEGORICAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']

export const BLUE = '#2a78d6'
export const BLUE_RAMP = ['#86b6ef', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab']

export const INK = {
  primary: '#0b0b0b',
  secondary: '#52514e',
  muted: '#898781',
  gridline: '#e1e0d9',
  baseline: '#c3c2b7',
}

export const STATUS = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
}

// 门店品类 → 分类色固定映射（颜色跟随实体，不跟随排名）
export const STORE_CATEGORY_COLOR: Record<string, string> = {
  拉面: '#2a78d6',
  轻食: '#eb6834',
  点心: '#1baf7a',
  三明治: '#eda100',
  日料: '#e87ba4',
}

export function fmtMoney(v: number): string {
  return '¥' + v.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}
