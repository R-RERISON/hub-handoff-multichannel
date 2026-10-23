import { ApiError } from '../workspaces/types'

const queueStateLabels: Record<string, string> = {
  ACTIVE: 'Ativo',
  ARCHIVED: 'Arquivado',
  CLOSED: 'Encerrado',
  DRAFT: 'Rascunho',
  OFFERED: 'Oferta pendente',
  PAUSED: 'Pausado',
  QUEUED: 'Na fila',
}

const presenceLabels: Record<string, string> = {
  AVAILABLE: 'Disponível',
  AWAY: 'Em pausa',
  OFFLINE: 'Indisponível',
}

const roleLabels: Record<string, string> = {
  ADMIN: 'Administrador',
  AUDITOR: 'Auditor',
  OPERATOR: 'Operador',
  SUPERVISOR: 'Supervisor',
}

const eventLabels: Record<string, string> = {
  ACCEPTED: 'Atendimento aceito',
  ACTIVE: 'Atendimento iniciado',
  CLOSED: 'Atendimento encerrado',
  DECLINED: 'Oferta recusada',
  OFFERED: 'Oferta criada',
  OFFERED_AUTO: 'Oferta automática criada',
  OFFER_EXPIRED: 'Oferta expirada',
  QUEUED: 'Solicitação entrou na fila',
  TRANSFERRED: 'Atendimento transferido',
}

export function queueStateLabel(state: string): string {
  return queueStateLabels[state] ?? 'Estado não reconhecido'
}

export function presenceLabel(presence: string): string {
  return presenceLabels[presence] ?? 'Presença não reconhecida'
}

export function roleLabel(role: string): string {
  return roleLabels[role] ?? 'Perfil não reconhecido'
}

export function eventLabel(event: string): string {
  return eventLabels[event] ?? 'Evento registrado'
}

export function userFacingError(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        return 'Sua sessão expirou. Entre novamente.'
      case 403:
        return 'Seu perfil não tem autorização para esta ação.'
      case 404:
        return 'Este item não está disponível no escopo atual. Atualize a tela.'
      case 409:
        return 'Os dados mudaram desde a última consulta. Atualize a tela antes de continuar.'
      case 422:
        return 'Revise os dados informados e tente novamente.'
      default:
        if (error.status >= 500) return 'O serviço local está temporariamente indisponível.'
        return fallback
    }
  }

  if (error instanceof TypeError) {
    return 'Não foi possível conectar ao serviço local. Verifique a conexão e atualize os dados.'
  }

  return fallback
}
