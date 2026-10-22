import { useEffect, useRef, useState } from 'react'
import { LockKeyhole, RefreshCw, ShieldCheck } from 'lucide-react'
import { ApiError, type Api, type ChatMessage } from './types'
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
  message_page:number
  event_page:number
  message_next_page:number|null
  event_next_page:number|null
  page_size:number
}

export default function ScopedVerifiedHistory({api}:{api:Api}) {
  const [queues,setQueues] = useState<GrantQueue[]>([])
  const [queueId,setQueueId] = useState('')
  const [page,setPage] = useState(1)
  const [listing,setListing] = useState<Listing|null>(null)
  const [selectedId,setSelectedId] = useState<string|null>(null)
  const [messagePage,setMessagePage] = useState(1)
  const [eventPage,setEventPage] = useState(1)
  const [detail,setDetail] = useState<VerifiedDetails|null>(null)
  const [loading,setLoading] = useState(false)
  const [detailLoading,setDetailLoading] = useState(false)
  const [error,setError] = useState('')
  const [refreshKey,setRefreshKey] = useState(0)
  const [grantsLoading,setGrantsLoading] = useState(true)
  const preferredQueueRef = useRef('')

  useEffect(()=>{
    let cancelled=false
    setGrantsLoading(true)
    api('/v1/me/queues').then(data=>{
      if(cancelled)return
      const available=data as GrantQueue[]
      setQueues(available)
      setQueueId(available.find(q=>q.id===preferredQueueRef.current)?.id??available[0]?.id??'')
    }).catch(()=>{
      if(cancelled)return
      // Fail closed in the VIEW too: no stale queue or message remains visible.
      setQueues([])
      setQueueId('')
      setListing(null)
      setSelectedId(null)
      setDetail(null)
      setError('Não foi possível validar as filas concedidas.')
    }).finally(()=>{if(!cancelled)setGrantsLoading(false)})
    return ()=>{cancelled=true}
  },[api,refreshKey])

  useEffect(()=>{
    if(!queueId||!queues.some(q=>q.id===queueId)){
      setListing(null)
      setSelectedId(null)
      setDetail(null)
      setLoading(false)
      setDetailLoading(false)
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
      .catch(error=>{
        if(cancelled)return
        setListing(null)
        setSelectedId(null)
        setDetail(null)
        if(error instanceof ApiError&&[401,403].includes(error.status)){
          setQueues([])
          setQueueId('')
          setError('A concessão foi revogada ou expirou. Os dados protegidos foram removidos.')
        }else{
          setError('Consulta indisponível; nenhum dado anterior foi mantido.')
        }
      })
      .finally(()=>{if(!cancelled)setLoading(false)})
    return ()=>{cancelled=true}
  },[api,queueId,queues,page,refreshKey])

  useEffect(()=>{
    if(!selectedId||!queueId){
      setDetail(null)
      setDetailLoading(false)
      return
    }
    let cancelled=false
    setDetail(null)
    setDetailLoading(true)
    setError('')
    api('/v1/handoffs/'+encodeURIComponent(selectedId)+
      '/verified-history?queue_id='+encodeURIComponent(queueId)+
      '&message_page='+messagePage+'&event_page='+eventPage)
      .then(data=>{if(!cancelled)setDetail(data as VerifiedDetails)})
      .catch(error=>{
        if(cancelled)return
        setDetail(null)
        if(error instanceof ApiError&&[401,403].includes(error.status)){
          setQueues([])
          setQueueId('')
          setListing(null)
          setSelectedId(null)
          setError('A concessão foi revogada ou expirou. Os dados protegidos foram removidos.')
        }else{
          setSelectedId(null)
          setError('O acesso ao segmento não pôde ser confirmado; o conteúdo foi removido.')
        }
      })
      .finally(()=>{if(!cancelled)setDetailLoading(false)})
    return ()=>{cancelled=true}
  },[api,queueId,selectedId,messagePage,eventPage,refreshKey])

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
      <select id="verified-history-queue" value={queueId} disabled={grantsLoading}
        onChange={e=>{
          preferredQueueRef.current=e.target.value
          setQueueId(e.target.value);setPage(1);setListing(null)
          setSelectedId(null);setDetail(null);setMessagePage(1);setEventPage(1)
        }}>
        {queues.length===0&&<option value="">{grantsLoading?'Validando concessões…':'Nenhuma fila autorizada'}</option>}
        {queues.map(q=><option value={q.id} key={q.id}>{q.name}</option>)}
      </select>
      <button className="outline" type="button" disabled={grantsLoading} onClick={()=>{
        // Never display previously fetched content while grants are being revalidated.
        preferredQueueRef.current=queueId
        setQueues([]);setQueueId('');setListing(null);setSelectedId(null)
        setDetail(null);setError('');setLoading(false);setDetailLoading(false)
        setPage(1);setMessagePage(1);setEventPage(1)
        setGrantsLoading(true);setRefreshKey(v=>v+1)
      }}><RefreshCw size={15}/> Atualizar permissões</button>
    </section>
    {error&&<div className="alert" role="alert">{error}</div>}
    {grantsLoading&&<p className="verified-history-access-state" role="status">
      Validando acesso às filas concedidas…
    </p>}
    {!grantsLoading&&!error&&queues.length===0&&
      <p className="verified-history-access-state" role="status">
        Nenhuma fila autorizada para consulta de histórico.
      </p>}
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
          <small aria-live="polite">Página {listing.page} · IDs restritos à fila selecionada</small>
        </header>
        <div className="history-list">
          {listing.tickets.map(t=><button key={t.session_id} type="button"
            className={'history-ticket '+(selectedId===t.session_id?'selected':'')}
            aria-pressed={selectedId===t.session_id}
            onClick={()=>{
              if(selectedId===t.session_id)return
              setMessagePage(1);setEventPage(1)
              setDetail(null);setDetailLoading(true)
              setSelectedId(t.session_id)
            }}>
            <strong>Sessão {t.session_id.slice(0,8)}…</strong>
            <small>Início do segmento: {formatTime(t.segment_started_at)}</small>
          </button>)}
          {listing.tickets.length===0&&<p className="empty-state">
            Nenhum segmento com evidência comprovada nesta página.
          </p>}
        </div>
        <div className="verified-history-pagination" role="navigation"
          aria-label="Paginação de atendimentos verificados">
          <button type="button" className="outline" disabled={loading||page<=1}
            aria-label="Página anterior de atendimentos"
            onClick={()=>{
              setListing(null);setLoading(true)
              setSelectedId(null);setDetail(null);setDetailLoading(false)
              setMessagePage(1);setEventPage(1);setPage(v=>v-1)
            }}>Anterior</button>
          <button type="button" className="outline"
            disabled={loading||listing.next_page===null}
            aria-label="Próxima página de atendimentos"
            onClick={()=>{
              setListing(null);setLoading(true)
              setSelectedId(null);setDetail(null);setDetailLoading(false)
              setMessagePage(1);setEventPage(1);setPage(v=>v+1)
            }}>
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
            Nenhuma mensagem comprovada nesta página do segmento.
          </p>}
        </div>
        <div className="verified-history-detail-pages" aria-label="Paginação de mensagens verificadas">
          <strong aria-live="polite">Mensagens · página {detail.message_page}</strong>
          <button type="button" className="outline"
            aria-label="Página anterior de mensagens" disabled={detailLoading||messagePage<=1}
            onClick={()=>{
              setDetail(null);setDetailLoading(true);setMessagePage(v=>v-1)
            }}>Anterior</button>
          <button type="button" className="outline"
            aria-label="Próxima página de mensagens"
            disabled={detailLoading||detail.message_next_page===null}
            onClick={()=>{
              setDetail(null);setDetailLoading(true);setMessagePage(v=>v+1)
            }}>Próxima</button>
        </div>
        <div className="history-events" role="region" aria-label="Eventos comprovados" tabIndex={0}>
          <b>Eventos comprovados</b>
          {detail.events.map((e,i)=><span key={i}>
            {e.type} · {e.actor} · {formatTime(e.at)}
          </span>)}
          {detail.events.length===0&&<p className="empty-state">
            Nenhum evento comprovado nesta página.
          </p>}
        </div>
        <div className="verified-history-detail-pages" aria-label="Paginação de eventos verificados">
          <strong aria-live="polite">Eventos · página {detail.event_page}</strong>
          <button type="button" className="outline"
            aria-label="Página anterior de eventos" disabled={detailLoading||eventPage<=1}
            onClick={()=>{
              setDetail(null);setDetailLoading(true);setEventPage(v=>v-1)
            }}>Anterior</button>
          <button type="button" className="outline"
            aria-label="Próxima página de eventos"
            disabled={detailLoading||detail.event_next_page===null}
            onClick={()=>{
              setDetail(null);setDetailLoading(true);setEventPage(v=>v+1)
            }}>Próxima</button>
        </div></>}
        </>}
      </section>
    </div>}
  </div>
}
