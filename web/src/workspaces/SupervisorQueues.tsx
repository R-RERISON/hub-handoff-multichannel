import { useCallback, useEffect, useRef, useState } from 'react'
import { Layers, RefreshCw } from 'lucide-react'
import { ConfirmDialog } from '../design-system/ConfirmDialog'
import { userFacingError } from '../design-system/presentation'
import { ApiError, type Api, type Operator, type Queue, type Ticket } from './types'

type RotationMember = {
  operator_id:string; name:string; online:boolean; presence:string
  occupied:number; capacity:number; eligible:boolean
  last_offered_at:string|null; total_offers:number
}
type PendingMembership = {
  queueId:string; queueName:string; operatorId:string; operatorName:string; enabled:boolean
}
type RotationState = 'loading'|'ready'|'error'|'denied'|'stale'
type Props = { queues:Queue[]; operators:Operator[]; tickets:Ticket[]; api:Api; onChanged:()=>Promise<void> }

export default function SupervisorQueues({queues,operators,tickets,api,onChanged}:Props){
  const [saving,setSaving] = useState(false)
  const [rotation,setRotation] = useState<Record<string,RotationMember[]>>({})
  const [rotationState,setRotationState] = useState<RotationState>('loading')
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [pendingMembership,setPendingMembership] = useState<PendingMembership|null>(null)
  const requestVersionRef = useRef(0)
  const loadPendingRef = useRef(false)
  const hasRotationRef = useRef(false)
  const membershipRequestRef = useRef(false)
  const membershipErrorRef = useRef<HTMLDivElement|null>(null)
  const membershipNoticeRef = useRef<HTMLDivElement|null>(null)

  useEffect(()=>{
    if(error)membershipErrorRef.current?.focus()
    else if(notice)membershipNoticeRef.current?.focus()
  },[error,notice])

  const load = useCallback(async ():Promise<boolean> => {
    if(loadPendingRef.current)return false
    loadPendingRef.current=true
    const requestId=++requestVersionRef.current
    try{
      if(queues.length===0){
        if(requestId!==requestVersionRef.current)return false
        hasRotationRef.current=false
        setRotation({})
        setRotationState('ready')
        setError('')
        return true
      }
      const items=await Promise.all(queues.map(q=>api('/v1/queues/'+q.id+'/rotation')))
      if(requestId!==requestVersionRef.current)return false
      hasRotationRef.current=true
      setRotation(Object.fromEntries(queues.map((q,i)=>[q.id,items[i].operators])))
      setRotationState('ready')
      setError('')
      return true
    }catch(e){
      if(requestId!==requestVersionRef.current)return false
      if(e instanceof ApiError&&[401,403,404].includes(e.status)){
        hasRotationRef.current=false
        setRotation({})
        setRotationState('denied')
      }else{
        setRotationState(hasRotationRef.current?'stale':'error')
      }
      setError(userFacingError(e,'Não foi possível consultar a ordem de distribuição. Atualize antes de continuar.'))
      return false
    }finally{
      if(requestId===requestVersionRef.current)loadPendingRef.current=false
    }
  },[queues,api])

  useEffect(()=>{
    requestVersionRef.current+=1
    loadPendingRef.current=false
    hasRotationRef.current=false
    setRotation({})
    setRotationState('loading')
    void load()
    const interval=window.setInterval(()=>{
      if(document.visibilityState==='visible')void load()
    },10000)
    return ()=>{
      window.clearInterval(interval)
      requestVersionRef.current+=1
      loadPendingRef.current=false
    }
  },[load])

  function requestMembership(queueId:string,operatorId:string,enabled:boolean){
    const operator=operators.find(item=>item.id===operatorId)
    const queue=queues.find(item=>item.id===queueId)
    if(!operator||!queue||rotationState!=='ready'||saving)return
    setPendingMembership({
      queueId,queueName:queue.name,operatorId,operatorName:operator.name,enabled,
    })
  }

  async function commitMembership(){
    if(!pendingMembership||membershipRequestRef.current||rotationState!=='ready')return
    membershipRequestRef.current=true
    const change=pendingMembership
    setSaving(true)
    setError('')
    setNotice('')
    try{
      await api('/v1/queues/'+change.queueId+'/members/'+change.operatorId,
        'PATCH',{enabled:change.enabled})
      setPendingMembership(null)
      const refreshed=await load()
      try{await onChanged()}catch{/* The local rotation refresh remains authoritative for this view. */}
      setNotice(refreshed
        ? change.enabled
          ? `${change.operatorName} foi adicionado à fila ${change.queueName}.`
          : `${change.operatorName} foi removido da fila ${change.queueName}.`
        : 'Alteração confirmada; atualize a fila para conferir o resultado.')
    }catch(e){
      setPendingMembership(null)
      if(e instanceof ApiError&&[401,403,404].includes(e.status)){
        hasRotationRef.current=false
        setRotation({})
        setRotationState('denied')
      }else{
        setRotationState(hasRotationRef.current?'stale':'error')
      }
      setError('Resultado não confirmado. '+userFacingError(e,'Atualize a lista antes de tentar novamente.'))
    }finally{
      membershipRequestRef.current=false
      setSaving(false)
    }
  }

  const confirmationDescription=pendingMembership
    ? `${pendingMembership.operatorName} será ${pendingMembership.enabled?'incluído na':'removido da'} rotação da fila ${pendingMembership.queueName}. Esta mudança afeta novas ofertas e não transfere conversas existentes.`
    : ''

  return <div className="section-stack">
    <section className="intro-banner"><div>
      <span className="eyebrow">SUPERVISÃO / ROTEAMENTO AUTOMÁTICO</span>
      <h2 tabIndex={-1} data-page-focus>Gerenciamento de filas</h2>
      <p>Solicitações são atribuídas automaticamente aos operadores online e disponíveis, respeitando capacidade e rodízio por fila.</p>
    </div><button className="outline" type="button" disabled={rotationState==='loading'}
      onClick={()=>void load()}><RefreshCw size={15}/> Atualizar posições</button></section>
    {error&&<div className="alert" role="alert" tabIndex={-1} data-page-focus
      ref={membershipErrorRef}>{error}</div>}
    {notice&&<div className="notice" role="status" aria-live="polite" tabIndex={-1}
      data-page-focus ref={membershipNoticeRef}>{notice}
      <button type="button" aria-label="Dispensar aviso" onClick={()=>setNotice('')}>×</button>
    </div>}
    {rotationState==='loading'&&<p className="panel queue-data-state" role="status" aria-live="polite">
      Consultando posições e vínculos autorizados…
    </p>}
    {rotationState==='stale'&&<p className="panel queue-data-state" role="status" aria-live="polite">
      Exibindo a última consulta confirmada. As alterações estão bloqueadas até a atualização.
    </p>}
    {rotationState==='denied'&&<p className="panel queue-data-state" role="status">
      O acesso à rotação foi removido. Os dados protegidos foram apagados.
    </p>}
    {rotationState==='ready'&&queues.length===0&&
      <p className="panel queue-data-state" role="status">Nenhuma fila disponível nesta operação.</p>}
    {queues.map(q=>{
      const pending=tickets.filter(t=>t.queue_id===q.id&&t.status==='QUEUED')
      const offers=tickets.filter(t=>t.queue_id===q.id&&t.status==='OFFERED')
      const members=rotation[q.id]??[]
      return <section className="panel queue-card" key={q.id}>
        <header className="queue-card__header"><div className="queue-card__heading">
          <span className="record-icon"><Layers size={19}/></span>
          <div><h3>{q.name}</h3><small>Ordem de chegada + rodízio persistente · {q.id.toUpperCase()}</small></div>
        </div><span className="status active">Automático</span></header>
        <div className="queue-card__metrics">
          <div><strong>{q.waiting}</strong><span>Na fila</span></div>
          <div><strong>{q.offered}</strong><span>Oferta pendente</span></div>
          <div><strong>{q.active}</strong><span>Atendimento ativo</span></div>
        </div>
        <div className="rotation-panel"><h4>Ordem atual de distribuição</h4>
          {rotationState==='ready'&&members.map((member,index)=><div className="rotation-member" key={member.operator_id}>
            <span className="rotation-rank">{index+1}</span><strong>{member.name}</strong>
            <span className={'status '+(member.eligible?'active':'closed')}>
              {member.eligible?'Elegível':!member.online?'Desconectado':
                member.presence==='AWAY'?'Em pausa':
                  member.presence==='OFFLINE'?'Indisponível':'Sem capacidade'}
            </span><small>{member.occupied}/{member.capacity} ocupado(s) · {member.total_offers} oferta(s) históricas</small>
          </div>)}
          {rotationState==='ready'&&members.length===0&&
            <p className="queue-empty" role="status">Não há operadores associados a esta fila.</p>}
        </div>
        <div className="queue-membership">
          <h4>Equipe vinculada à fila</h4>
          <p>Vínculos determinam quais operadores podem receber ofertas desta fila.</p>
          {rotationState==='ready'&&operators.map(operator=>{
            const exists=members.some(member=>member.operator_id===operator.id)
            return <div className="queue-member" key={operator.id}>
              <span>{operator.name}</span>
              <button className="outline small" type="button"
                aria-label={`${exists?'Remover':'Adicionar'} ${operator.name} ${exists?'da':'à'} fila ${q.name}`}
                disabled={saving||rotationState!=='ready'}
                onClick={()=>requestMembership(q.id,operator.id,!exists)}>
                {exists?'Remover da fila':'Adicionar à fila'}
              </button>
            </div>
          })}
          {rotationState!=='ready'&&<p role="status">Vínculos indisponíveis até validar a rotação.</p>}
        </div>
        {pending.map(ticket=><div className="queue-request" key={ticket.id}>
          <div><strong>{ticket.requester_label}</strong><small>{ticket.subject} · Aguardando disponibilidade</small></div>
          <span className="status queued">Na fila</span>
        </div>)}
        {offers.map(ticket=><div className="queue-request queue-request--offer" key={ticket.id}>
          <div><strong>{ticket.requester_label}</strong>
            <small>{ticket.subject} · Oferta reservada a {operators.find(o=>o.id===ticket.operator_id)?.name??'operador'}</small></div>
          <span className="status offered">Aguardando aceite</span>
        </div>)}
      </section>
    })}
    <p className="operational-note">O operador que recebe a oferta vai ao fim da ordem de sua fila. Caso seja o único elegível, poderá receber novamente quando tiver capacidade; recusas têm um intervalo de espera para evitar reofertas imediatas.</p>
    <ConfirmDialog open={!!pendingMembership}
      title={pendingMembership
        ? pendingMembership.enabled
          ? `Adicionar ${pendingMembership.operatorName} à fila ${pendingMembership.queueName}?`
          : `Remover ${pendingMembership.operatorName} da fila ${pendingMembership.queueName}?`
        : 'Confirmar alteração de equipe'}
      description={confirmationDescription}
      confirmLabel={pendingMembership?.enabled?'Adicionar operador':'Remover operador'}
      busy={saving} danger={!pendingMembership?.enabled}
      onCancel={()=>setPendingMembership(null)} onConfirm={()=>void commitMembership()}/>
  </div>
}
