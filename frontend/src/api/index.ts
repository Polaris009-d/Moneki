import axios from 'axios'
import type { Summary, DailyPoint, TopProduct, StoreCategory, Insight, ChatResponse } from '../types'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

export async function fetchSummary(start?: string, end?: string): Promise<Summary> {
  return (await http.get('/dashboard/summary', { params: { start_date: start, end_date: end } })).data
}

export async function fetchDaily(start?: string, end?: string): Promise<DailyPoint[]> {
  return (await http.get('/dashboard/daily', { params: { start_date: start, end_date: end } })).data
}

export async function fetchTopProducts(start?: string, end?: string, limit = 10): Promise<TopProduct[]> {
  return (await http.get('/dashboard/top-products', { params: { start_date: start, end_date: end, limit } })).data
}

export async function fetchStoreCategory(start?: string, end?: string): Promise<StoreCategory[]> {
  return (await http.get('/dashboard/store-category', { params: { start_date: start, end_date: end } })).data
}

export async function fetchInsights(start?: string, end?: string): Promise<Insight[]> {
  return (await http.get('/insights', { params: { start_date: start, end_date: end } })).data.insights
}

export async function postChat(question: string, conversationId?: string): Promise<ChatResponse> {
  return (await http.post('/chat', { question, conversation_id: conversationId })).data
}
