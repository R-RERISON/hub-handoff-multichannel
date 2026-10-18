import { useCallback, useEffect, useState } from 'react'
import { Layers, RefreshCw } from 'lucide-react'
import type { Api, Operator, Queue, Ticket } from './types'

type RotationMember = {
  operator_id:string; name:string; online:boolean; presence:string
  occupied:number; capacity:number; eligible:boolean
  last_offered_at:string|null; total_offers:number
}
type Props = { queues:Queue[]; operators:Operator[]; tickets:Ticket[]; api:Api; onChanged:()=>Promise<void> }

export default function SupervisorQueues({queues,operators,tickets,api,onChanged}:Props){
  const [saving,setSaving] = useState(false)
  const [rotation,setRotation] = useState<Record<string,RotationMember[]>>({})
  const [error,setError] = useState('')
  const load=useCallback(async()=>{
    try{
      const items=await Promise.all(queues.map(q=>api('/v1/queues/'+q.id+'/rotation')))
      setRotation(Object.fromEntries(queues.map((q,i)=>[q.id,items[i].operators])))
      setError('')
    }catch(e){setError((e as Error).message)}
  },[queues,api])
  useEffect(()=>{
    void load()
    const interval=window.setInterval(()=>{
      if(document.visibilityState==='visible')void load()
    },10000)
    return ()=>window.clearInterval(interval)
  },[load])
  async function membership(queueId:string,operatorId:string,enabled:boolean){
    setSaving(true);setError('')
    try{
      await api('/v1/queues/'+queueId+'/members/'+operatorId,'PATCH',{enabled})
      await Promise.all([load(),onChanged()])
    }catch(e){setError((e as Error).message)}
    finally{setSaving(false)}
  }
  return <div className="section-stack">
    <section className="intro-banner"><div>
      <span className="eyebrow">SUPERVISÃO / ROTEAMENTO AUTOMÁTICO</span>
      <h2>Gerenciamento de filas</h2>
      <p>Solicitações são atribuídas automaticamente aos operadores online e disponíveis, respeitando capacidade e rodízio por fila.</p>
    </div><button className="outline" onClick={()=>void load()}><RefreshCw size={15}/> Atualizar posições</button></section>
    {error&&<div className="alert" role="alert">{error}</div>}
    {queues.map(q=>{
      const pending=tickets.filter(t=>t.queue_id===q.id&&t.status==='QUEUED')
      const offers=tickets.filter(t=>t.queue_id===q.id&&t.status==='OFFERED')
      return <section className="panel queue-card" key={q.id}>
        <header className="queue-card__header"><div className="queue-card__heading">
          <span className="record-icon"><Layers size={19}/></span>
          <div><h3>{q.name}</h3><small>Distribuição FIFO + rodízio persistente · {q.id.toUpperCase()}</small></div>
        </div><span className="status active">Automático</span></header>
        <div className="queue-card__metrics">
          <div><strong>{q.waiting}</strong><span>Na fila</span></div>
          <div><strong>{q.offered}</strong><span>Oferta pendente</span></div>
          <div><strong>{q.active}</strong><span>Atendimento ativo</span></div>
        </div>
        <div className="rotation-panel"><h4>Ordem atual de distribuição</h4>
          {rotation[q.id]?.map((m,i)=><div className="rotation-member" key={m.operator_id}>
            <span className="rotation-rank">{i+1}</span><strong>{m.name}</strong>
            <span className={'status '+(m.eligible?'active':'closed')}>
              {m.eligible?'Elegível':!m.online?'Desconectado':
                m.presence!=='AVAILABLE'?'Em pausa':'Sem capacidade'}
            </span><small>{m.occupied}/{m.capacity} ocupado(s) · {m.total_offers} oferta(s) históricas</small>
          </div>)}
          {!rotation[q.id]?.length&&<p className="queue-empty">Não há operadores associados a esta fila.</p>}
        </div>
        <div className="queue-membership">
          <h4>Equipe vinculada à fila</h4>
          <p>Vínculos determinam quais operadores podem receber ofertas desta fila.</p>
          {operators.map(op=>{
            const exists=(rotation[q.id]??[]).some(member=>member.operator_id===op.id)
            return <div className="queue-member" key={op.id}>
              <span>{op.name}</span>
              <button className="outline small" disabled={saving}
                onClick={()=>void membership(q.id,op.id,!exists)}>
                {exists?'Remover da fila':'Adicionar à fila'}
              </button>
            </div>
          })}
        </div>
        {pending.map(t=><div className="queue-request" key={t.id}>
          <div><strong>{t.requester_label}</strong><small>{t.subject} · Aguardando disponibilidade</small></div>
          <span className="status queued">Na fila</span>
        </div>)}
        {offers.map(t=><div className="queue-request queue-request--offer" key={t.id}>
          <div><strong>{t.requester_label}</strong>
            <small>{t.subject} · Oferta reservada a {operators.find(o=>o.id===t.operator_id)?.name??t.operator_id}</small></div>
          <span className="status offered">Aguardando aceite</span>
        </div>)}
      </section>
    })}
    <p className="operational-note">O operador que recebe a oferta vai ao fim da ordem de sua fila. Caso seja o único elegível, poderá receber novamente quando tiver capacidade; recusas possuem cooldown para evitar reofertas imediatas.</p>
  </div>
}
