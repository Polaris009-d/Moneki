export interface Summary {
  revenue: number
  order_count: number
  valid_order_count: number
  avg_order_value: number
}

export interface DailyPoint {
  date: string
  revenue: number
  order_count: number
  avg_order_value: number
}

export interface TopProduct {
  product_name: string
  product_category: string
  revenue: number
  qty: number
  order_count: number
}

export interface StoreCategory {
  category: string
  revenue: number
  order_count: number
}

export interface Insight {
  type: string
  title: string
  severity: string
  text: string
  data: any
}

export interface Evidence {
  tool: string
  metric: string
  period: string
  record_count: number
}

export interface ChatResponse {
  answer: string
  data: any
  evidence: Evidence | null
  tool_used: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  data?: any
  evidence?: Evidence | null
  tool_used?: string | null
}
