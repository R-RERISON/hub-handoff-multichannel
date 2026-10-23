import {
  Activity, ArrowRight, Clock3, Headset, Layers, MessageSquareText,
  Users
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { DashboardSnapshot } from './types'
import { EmptyState } from '../design-system/EmptyState'
import { queueStateLabel } from '../design-system/presentation'

type Props = { snapshot: DashboardSnapshot }

export default function SupervisorOverview({ snapshot }: Props) {
  const navigate = useNavigate()
  const active = snapshot.handoffs.filter(t => t.status === 'ACTIVE').length
  const offered = snapshot.handoffs.filter(t => t.status === 'OFFERED').length
  const waiting = snapshot.queues.reduce((total, q) => total + q.waiting, 0)
  const capacity = snapshot.operators.filter(
    o => o.presence === 'AVAILABLE' && o.active + (o.offered ?? 0) < o.capacity
  ).length

  const metrics = [
    { label: 'Atendimentos ativos', value: active, icon: <MessageSquareText size={20}/>, detail: 'Conversas em atendimento' },
    { label: 'Aguardando em filas', value: waiting, icon: <Clock3 size={20}/>, detail: 'Solicitações ainda não ofertadas' },
    { label: 'Ofertas pendentes', value: offered, icon: <Layers size={20}/>, detail: 'Aguardando aceite do operador' },
    { label: 'Operadores com capacidade', value: capacity, icon: <Users size={20}/>, detail: 'Disponíveis para novas ofertas' },
  ]
  return <div className="section-stack">
    <section className="intro-banner">
      <div><span className="eyebrow">CENTRAL DE SUPERVISÃO</span>
        <h2 tabIndex={-1} data-page-focus>Visão geral da operação</h2>
        <p>Acompanhe filas, capacidade e atendimentos demonstrativos desta operação local.</p>
      </div>
      <button className="primary" onClick={() => navigate('/supervisao/filas')}>
        Gerenciar filas <ArrowRight size={16}/>
      </button>
    </section>
    <div className="overview-metrics">
      {metrics.map(m => <div className="overview-metric panel" key={m.label}>
        <div className="overview-metric__label">{m.label}<span>{m.icon}</span></div>
        <strong>{m.value}</strong><small>{m.detail}</small>
      </div>)}
    </div>
    <div className="overview-grid">
      <section className="panel overview-panel">
        <div className="panel-header"><div><h3>Estado das filas</h3>
          <p>Solicitações em espera, ofertadas e em andamento</p></div>
          <button className="text-link" onClick={() => navigate('/supervisao/filas')}>Ver filas <ArrowRight size={14}/></button>
        </div>
        {snapshot.queues.length === 0 && <EmptyState className="empty-state">Nenhuma fila cadastrada.</EmptyState>}
        {snapshot.queues.map(q => <div className="overview-queue" key={q.id}>
          <div><b>{q.name}</b><small>{q.id.toUpperCase()}</small></div>
          <div className="queue-stats"><span>{q.waiting} aguardando</span><span>{q.offered} ofertado(s)</span><span>{q.active} ativo(s)</span></div>
        </div>)}
      </section>
      <section className="panel overview-panel">
        <div className="panel-header"><div><h3>Saúde operacional</h3>
          <p>Indicadores da POC e dependências</p></div></div>
        <div className="health-line"><span><Activity size={17}/> API local e SQLite</span><b>Sem monitoramento em tempo real</b></div>
        <div className="health-line"><span><Activity size={17}/> Mensagens locais pendentes de integração</span><b>{snapshot.outbox.pending} pendente(s) · não enviada(s)</b></div>
        <div className="health-line"><span><Headset size={17}/> Adapter Microsoft Teams</span><b>Não instalado</b></div>
        <p className="operational-note">As respostas registradas localmente não são enviadas aos usuários. Esta versão utiliza apenas dados simulados.</p>
      </section>
    </div>
    <section className="panel overview-panel">
      <div className="panel-header"><div><h3>Atendimentos recentes</h3>
        <p>Visão da supervisão, sem interferência nas respostas do operador</p></div>
        <button className="text-link" onClick={() => navigate('/supervisao/conversas')}>Consultar histórico <ArrowRight size={14}/></button>
      </div>
      {snapshot.handoffs.slice(0,5).map(t => <div className="recent-item" key={t.id}>
        <div><b>{t.requester_label}</b><small>{t.subject} · {t.queue_id.toUpperCase()}</small></div>
        <span className={'status '+t.status.toLowerCase()}>{queueStateLabel(t.status)}</span>
      </div>)}
      {snapshot.handoffs.length===0 && <EmptyState className="empty-state">Ainda não há solicitações. Utilize o Laboratório para criar uma.</EmptyState>}
    </section>
  </div>
}
