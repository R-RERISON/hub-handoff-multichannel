export type Ticket = {
  id: string
  operation_id: string
  integration_id: string
  queue_id: string
  requester_label: string
  subject: string
  status: string
  operator_id: string | null
  created_at: string
}

export type Queue = {
  id: string
  name: string
  waiting: number
  offered: number
  active: number
}

export type Operator = {
  id: string
  name: string
  presence: string
  capacity: number
  active: number
  offered?: number
}

export type ChatMessage = {
  id: string
  sender: string
  content: string
  created_at: string
}

export type DashboardSnapshot = {
  handoffs: Ticket[]
  queues: Queue[]
  operators: Operator[]
  outbox: { total: number; pending: number }
}

export type Api = (
  path: string,
  method?: string,
  body?: object,
  extra?: Record<string, string>
) => Promise<any>

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })

export const initials = (name: string) =>
  name.split(' ').slice(0, 2).map(part => part[0]).join('').toUpperCase()
