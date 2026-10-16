import { useEffect, useState } from 'react'
import { LockKeyhole, RefreshCw, ShieldCheck } from 'lucide-react'
import type { Api, ChatMessage } from './types'
import { formatTime } from './types'

type GrantQueue = {id:string;name:string;operation_id:string}
type TicketScope = {session_id:string;segment_started_at:string}
type Listing = {
  schema_ready:boolean
  tickets:TicketScope[]
  next_page:number|null
  page:number
  partial_history:true
}
type VerifiedDetails = {
  messages:ChatMessage[]
  events:{type:string;actor:string;at:string}[]
  partial_history:true
}

export default function ScopedVerifiedHistory({api}:{api:Api}) {
  const [queues,setQueues] = useState<GrantQueue[]>([])
  const [queueId,setQueueId] = useState('')
  const [page,setPage] = useState(1)
  const [listing,setListing] = useState<Listing|null>(null)
  const [selectedId,setSelectedId] = useState<string|null>(null)
  const [detail,setDetail] = useState<VerifiedDetails|null>(null)
  const [loading,setLoading] = useState(false)
  const [detailLoading,setDetailLoading] = useState(false)
  const [error,setError] = useState('')
  const [refreshKey,setRefreshKey] = useState(0)

  useEffect(()=>{
    let cancelled=false
    api('/v1/me/queues').then(data=>{
      if(cancelled)return
      const available=data as GrantQueue[]
      setQueues(available)
      setQueueId(current=>available.some(q=>q.id===current)?current:(available[0]?.id??''))
    }).catch(()=>{
      if(!cancelled)setError('Não foi possível consultar as filas concedidas.')
    })
    return ()=>{cancelled=true}
  },[api,refreshKey])

  useEffect(()=>{
    if(!queueId){
      setListing(null)
      return
    }
    let cancelled=false
    setLoading(true)
    setListing(null)
    setError('')
    setSelectedId(null)
    setDetail(null)
    api('/v1/history/verified-sessions?queue_id='+encodeURIComponent(queueId)+'&page='+page)
      .then(data=>{
        if(cancelled)return
        setListing(data as Listing)
      })
      .catch(()=>{
        if(!cancelled)setError('Consulta indisponível ou permissão de fila revogada.')
      })
      .finally(()=>{if(!cancelled)setLoading(false)})
    return ()=>{cancelled=true}
  },[api,queueId,page,refreshKey])

  useEffect(()=>{
    if(!selectedId||!queueId){
      setDetail(null)
      return
    }
    let cancelled=false
    setDetail(null)
    setDetailLoading(true)
    setError('')
    api('/v1/handoffs/'+encodeURIComponent(selectedId)+
      '/verified-history?queue_id='+encodeURIComponent(queueId))
      .then(data=>{if(!cancelled)setDetail(data as VerifiedDetails)})
      .catch(()=>{
        if(!cancelled)setError('O acesso ao segmento foi negado ou a concessão mudou.')
      })
      .finally(()=>{if(!cancelled)setDetailLoading(false)})
    return ()=>{cancelled=true}
  },[api,queueId,selectedId,refreshKey])

  return <div className="section-stack">
    <section className="panel verified-history-intro">
      <div><span className="eyebrow">SPEC-006B / PROVENIÊNCIA COMPROVADA</span>
        <h3>Histórico autorizado por fila</h3>
        <p>Apenas evidências registradas e verificadas nesta fila. O conteúdo de outras filas,
          notas internas de transferência e histórico sem comprovação são omitidos.</p>
      </div>
      <span className="verified-history-label"><ShieldCheck size={15}/> Somente leitura</span>
    </section>
    <section className="verified-history-toolbar panel">
      <label htmlFor="verified-history-queue">Fila com acesso concedido</label>
      <select id="verified-history-queue" value={queueId}
        onChange={e=>{
          setQueueId(e.target.value);setPage(1)
          setSelectedId(null);setDetail(null)
        }}>
        {queues.length===0&&<option value="">Nenhuma fila autorizada</option>}
        {queues.map(q=><option value={q.id} key={q.id}>{q.name}</option>)}
      </select>
      <button className="outline" type="button" onClick={()=>{
        setPage(1);setSelectedId(null);setDetail(null);setRefreshKey(v=>v+1)
      }}><RefreshCw size={15}/> Atualizar permissões</button>
    </section>
    {error&&<div className="alert" role="alert">{error}</div>}
    <div className="verified-history-warning" role="status">
      <LockKeyhole size={16}/>
      Visualização parcial: a ausência de itens aqui não significa ausência de mensagens no atendimento.
    </div>
    {loading&&<p className="empty-state" role="status">Consultando segmentos autorizados…</p>}
    {listing&&!listing.schema_ready&&<section className="panel verified-history-unavailable">
      <h3>Proveniência por segmento indisponível neste banco</h3>
      <p>O SQLite POC original ainda não está versionado. Nenhum histórico foi desbloqueado;
        a homologação de migração continua restrita a cópias isoladas.</p>
    </section>}
    {listing?.schema_ready&&<div className="history-layout verified-history-layout">
      <section className="panel history-sidebar">
        <header className="verified-history-panel-title">
          <b>Atendimentos com evidência verificada</b>
          <small>Página {listing.page} · IDs restritos à fila selecionada</small>
        </header>
        <div className="history-list">
          {listing.tickets.map(t=><button key={t.session_id} type="button"
            className={'history-ticket '+(selectedId===t.session_id?'selected':'')}
            onClick={()=>{setSelectedId(t.session_id);setDetail(null)}}>
            <strong>Sessão {t.session_id.slice(0,8)}…</strong>
            <small>Início do segmento: {formatTime(t.segment_started_at)}</small>
          </button>)}
          {listing.tickets.length===0&&<p className="empty-state">
            Nenhum segmento com evidência comprovada nesta página.
          </p>}
        </div>
        <div className="verified-history-pagination">
          <button type="button" className="outline" disabled={page<=1} onClick={()=>{
            setPage(v=>v-1);setSelectedId(null);setDetail(null)
          }}>Anterior</button>
          <button type="button" className="outline" disabled={listing.next_page===null}
            onClick={()=>{setPage(v=>v+1);setSelectedId(null);setDetail(null)}}>
            Próxima
          </button>
        </div>
      </section>
      <section className="panel history-details">
        {!selectedId&&<div className="center-empty">
          <LockKeyhole size={32}/><h3>Selecione um segmento autorizado</h3>
          <p>Uma fila concedida não autoriza o restante da conversa.</p>
        </div>}
        {selectedId&&<><header className="history-details__header">
          <div><h3>Registro verificado · {selectedId.slice(0,8)}…</h3>
            <p>Conteúdo exclusivamente da fila selecionada</p></div>
          <span className="verified-history-label">PARCIAL</span>
        </header>
        {detailLoading&&<p className="empty-state" role="status">Carregando histórico autorizado…</p>}
        {detail&&<><div className="history-messages">
          <div className="chat-notice">HISTÓRICO PARCIAL · SOMENTE LEITURA</div>
          {detail.messages.map(m=><div key={m.id}
            className={'bubble-row '+(m.sender==='OPERATOR'?'right':'')}>
            <div className="bubble"><b>{m.sender==='OPERATOR'?'Operador':'Usuário'}</b>
              <p>{m.content}</p><small>{formatTime(m.created_at)}</small></div>
          </div>)}
          {detail.messages.length===0&&<p className="empty-state">
            Nenhuma mensagem comprovada neste segmento.
          </p>}
        </div><div className="history-events"><b>Eventos comprovados</b>
          {detail.events.map((e,i)=><span key={i}>
            {e.type} · {e.actor} · {formatTime(e.at)}
          </span>)}
        </div></>}
        </>}
      </section>
    </div>}
  </div>
}
