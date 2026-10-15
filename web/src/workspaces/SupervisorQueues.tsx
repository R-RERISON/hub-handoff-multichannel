import { ArrowRight, Layers, UserRoundCheck } from 'lucide-react'
import type { Operator, Queue, Ticket } from './types'

type Props = {
  queues: Queue[]
  operators: Operator[]
  tickets: Ticket[]
  busy: boolean
  onOffer: (queueId:string)=>Promise<void>
  onOpenOperator: (operatorId:string)=>void
}

export default function SupervisorQueues({queues,operators,tickets,busy,onOffer,onOpenOperator}: Props) {
  return <div className="section-stack">
    <section className="intro-banner">
      <div><span className="eyebrow">SUPERVISÃO / DISTRIBUIÇÃO</span>
        <h2>Gerenciamento de filas</h2>
        <p>Monitore atendimentos aguardando, ofertas pendentes e a capacidade das equipes.</p></div>
      <div className="banner-icon"><Layers size={28}/></div>
    </section>
    {queues.map(q => {
      const offers = tickets.filter(t => t.queue_id===q.id && t.status==='OFFERED')
      const pending = tickets.filter(t => t.queue_id===q.id && t.status==='QUEUED')
      return <section className="panel queue-card" key={q.id}>
        <header className="queue-card__header"><div className="queue-card__heading">
            <span className="record-icon"><Layers size={19}/></span><div><h3>{q.name}</h3><small>Operação demonstrativa · {q.id.toUpperCase()}</small></div>
          </div>
          <button className="primary" disabled={busy||q.waiting===0} onClick={()=>void onOffer(q.id)}>
            <UserRoundCheck size={16}/> Ofertar próximo <ArrowRight size={15}/>
          </button>
        </header>
        <div className="queue-card__metrics">
          <div><strong>{q.waiting}</strong><span>Na fila</span></div>
          <div><strong>{q.offered}</strong><span>Ofertados</span></div>
          <div><strong>{q.active}</strong><span>Em atendimento</span></div>
        </div>
        {pending.map(t => <div className="queue-request" key={t.id}>
          <div><strong>{t.requester_label}</strong><small>{t.subject} · Aguardando distribuição</small></div>
          <span className="status queued">Na fila</span>
        </div>)}
        {offers.map(t => {
          const operator = operators.find(o => o.id===t.operator_id)
          return <div className="queue-request queue-request--offer" key={t.id}>
            <div><strong>{t.requester_label}</strong><small>{t.subject} · Oferta enviada para {operator?.name??t.operator_id}</small></div>
            <button className="outline small" onClick={()=>t.operator_id&&onOpenOperator(t.operator_id)}>
              Abrir Mesa do Operador <ArrowRight size={14}/>
            </button>
          </div>
        })}
        {pending.length===0&&offers.length===0&&<p className="queue-empty">Sem solicitações aguardando ou ofertas pendentes nesta fila.</p>}
      </section>
    })}
    <p className="operational-note">A oferta reserva capacidade por até dois minutos. Uma solicitação ofertada deixa de contar como “Na fila” até ser aceita, recusada ou expirar.</p>
  </div>
}
