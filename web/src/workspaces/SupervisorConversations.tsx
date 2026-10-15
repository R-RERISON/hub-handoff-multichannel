import { useEffect, useState } from 'react'
import { ArrowLeft, MessageSquareText, Search } from 'lucide-react'
import type { Api, ChatMessage, Ticket } from './types'
import { formatTime } from './types'

type Props = {tickets:Ticket[];api:Api}
type Timeline = { events: {type:string;actor:string;at:string}[]; transfers: {reason:string;from_queue_id:string;to_queue_id:string}[] }

export default function SupervisorConversations({tickets,api}:Props) {
  const [selectedId,setSelectedId] = useState<string|null>(null)
  const [filter,setFilter] = useState('all')
  const [search,setSearch] = useState('')
  const [messages,setMessages] = useState<ChatMessage[]>([])
  const [timeline,setTimeline] = useState<Timeline|null>(null)
  const [error,setError] = useState('')
  const selected = tickets.find(t=>t.id===selectedId)
  const visible = tickets.filter(t =>
    (filter==='all'||t.status===filter) &&
    (t.requester_label.toLocaleLowerCase().includes(search.toLocaleLowerCase())||
     t.subject.toLocaleLowerCase().includes(search.toLocaleLowerCase())||
     t.id.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  )

  useEffect(()=>{
    if(!selectedId) return
    let cancelled=false
    setError('')
    Promise.all([
      api('/v1/handoffs/'+selectedId+'/messages'),
      api('/v1/handoffs/'+selectedId+'/timeline')
    ]).then(([m,t])=>{
      if(cancelled)return
      setMessages(m as ChatMessage[])
      setTimeline(t as Timeline)
    }).catch(e=>!cancelled&&setError((e as Error).message))
    return ()=>{cancelled=true}
  },[selectedId,api])

  return <div className="section-stack">
    <section className="intro-banner">
      <div><span className="eyebrow">SUPERVISÃO / HISTÓRICO</span>
        <h2>Conversas da operação</h2>
        <p>Consulte o estado, o histórico e as evidências das sessões. O atendimento é realizado exclusivamente na Mesa do Operador.</p>
      </div>
      <div className="banner-icon"><MessageSquareText size={28}/></div>
    </section>
    <div className="history-layout">
      <section className="panel history-sidebar">
        <div className="history-filter">
          <label className="search-field"><Search size={15}/><input value={search}
            placeholder="Buscar nome, assunto ou ID" onChange={e=>setSearch(e.target.value)}
            aria-label="Buscar conversas"/></label>
          <select aria-label="Filtrar estado" value={filter} onChange={e=>setFilter(e.target.value)}>
            <option value="all">Todos os estados</option><option value="QUEUED">Na fila</option>
            <option value="OFFERED">Ofertadas</option><option value="ACTIVE">Ativas</option>
            <option value="CLOSED">Encerradas</option>
          </select>
        </div>
        <div className="history-list">
          {visible.map(t=><button key={t.id} className={'history-ticket '+(selectedId===t.id?'selected':'')}
            onClick={()=>{setSelectedId(t.id);setMessages([]);setTimeline(null)}}>
            <strong>{t.requester_label}</strong><small>{t.subject}</small>
            <span className={'status '+t.status.toLowerCase()}>{t.status}</span>
          </button>)}
          {visible.length===0&&<p className="empty-state">Nenhuma sessão corresponde ao filtro.</p>}
        </div>
      </section>
      <section className="panel history-details">
        {selected?<><header className="history-details__header"><div>
            <h3>{selected.requester_label}</h3><p>{selected.subject} · {selected.queue_id.toUpperCase()}</p>
          </div><span className={'status '+selected.status.toLowerCase()}>{selected.status}</span></header>
          <div className="history-meta">Sessão: {selected.id} · Bot: {selected.integration_id} · Operador: {selected.operator_id??'Não atribuído'}</div>
          {error&&<div className="alert" role="alert">{error}</div>}
          <div className="history-messages">
            <div className="chat-notice">HISTÓRICO DE SIMULAÇÃO · SOMENTE LEITURA</div>
            {messages.map(m=><div className={'bubble-row '+(m.sender==='OPERATOR'?'right':'')} key={m.id}>
              <div className="bubble"><b>{m.sender==='OPERATOR'?'Operador':'Usuário'}</b>
                <p>{m.content}</p><small>{formatTime(m.created_at)}</small></div>
            </div>)}
            {messages.length===0&&<p className="empty-state">Sem mensagens registradas.</p>}
          </div>
          <div className="history-events"><b>Trilha de auditoria</b>
            {timeline?.events?.map((e,i)=><span key={i}>{e.type} · {e.actor} · {formatTime(e.at)}</span>)}
            {timeline?.transfers?.map((t,i)=><span key={'t'+i}>Transferência {t.from_queue_id} → {t.to_queue_id}: {t.reason}</span>)}
          </div>
        </>:<div className="center-empty"><MessageSquareText size={37}/>
            <h3>Selecione uma sessão</h3><p>Consulte as mensagens e o histórico sem interferir no atendimento.</p>
          </div>}
      </section>
    </div>
  </div>
}
