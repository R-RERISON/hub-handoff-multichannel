import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowRightLeft, CheckCircle2, Clock3, Headset, Inbox, MessageSquareText,
  RefreshCw, Send, ShieldAlert, XCircle
} from 'lucide-react'

type Operator = {id: string; name: string; presence: string; capacity: number; active: number; offered?: number}
type Queue = {id: string; name: string; waiting: number}
type Handoff = {id: string; operator_id: string|null; queue_id: string; subject: string; requester_label: string; status: string}
type Offer = {offer_id: string; session_id: string; operator_id: string; queue_id: string; subject: string; requester_label: string; expires_at: string}
type Work = {
  operator: {id: string; name: string; presence: string; capacity: number}
  offers: Offer[]
  active: Handoff[]
}
type ChatMessage = {id: string; content: string; sender: string; created_at: string}
type TransferTarget = {id: string; name: string}
type TransferTargetResponse = {session_id: string; source_queue_id: string; destinations: TransferTarget[]}
type TransferNote = {
  from_queue_id: string; to_queue_id: string; operator_id: string; reason: string; at: string
  from_operator_name?: string; from_queue_name?: string; to_queue_name?: string
}
type TimelineResponse = {
  events: {type:string;actor:string}[]
  transfers: TransferNote[]
}
type Api = (path: string, method?: string, body?: object, extra?: Record<string,string>)=>Promise<any>
type Props = {
  operators: Operator[]
  queues: Queue[]
  preferredOperatorId: string
  lockedIdentity?: boolean
  api: Api
  onChanged: ()=>Promise<void>
  onGoQueues: ()=>void
}

const labelTime=(value:string)=>new Date(value).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})

export default function OperatorDesk({operators,queues,preferredOperatorId,lockedIdentity=false,api,onChanged,onGoQueues}:Props) {
  const [operatorId,setOperatorId] = useState(preferredOperatorId)
  const [alertOffer,setAlertOffer] = useState<Offer|null>(null)
  const [browserAlerts,setBrowserAlerts] = useState(false)
  const notified = useRef(new Set<string>())
  const browserAlertsRef = useRef(false)
  const acceptButtonRef = useRef<HTMLButtonElement|null>(null)
  const messagePaneRef = useRef<HTMLDivElement|null>(null)
  const [work,setWork] = useState<Work|null>(null)
  const [selectedId,setSelectedId] = useState<string|null>(null)
  const [messages,setMessages] = useState<ChatMessage[]>([])
  const [reply,setReply] = useState('')
  const [targetQueue,setTargetQueue] = useState('')
  const [transferTargets,setTransferTargets] = useState<TransferTarget[]>([])
  const [transferLoading,setTransferLoading] = useState(false)
  const [transferReason,setTransferReason] = useState('Encaminhamento para a equipe especializada')
  const [transferOpen,setTransferOpen] = useState(false)
  const [auditOpen,setAuditOpen] = useState(false)
  const [mobilePanel,setMobilePanel] = useState<'work'|'chat'>('work')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [timeline,setTimeline] = useState<string[]>([])
  const [transferNotes,setTransferNotes] = useState<TransferNote[]>([])
  const [offerTransfer,setOfferTransfer] = useState<TransferNote|null>(null)
  const selected = work?.active.find(h=>h.id===selectedId) ?? null
  const queueTitle = (id:string) => transferTargets.find(q=>q.id===id)?.name
    ?? queues.find(q=>q.id===id)?.name ?? id
  const latestTransfer = transferNotes.at(-1)??null
  const transferHeading = (note:TransferNote) =>
    (note.from_queue_name??note.from_queue_id)+' → '+(note.to_queue_name??note.to_queue_id)
  const transferAuthor = (note:TransferNote) =>
    note.from_operator_name??note.operator_id

  useEffect(()=>setOperatorId(preferredOperatorId),[preferredOperatorId])
  useEffect(()=>{browserAlertsRef.current=browserAlerts},[browserAlerts])
  useEffect(()=>{if(alertOffer)acceptButtonRef.current?.focus()},[alertOffer?.offer_id])

  const reload = useCallback(async () => {
    if (!operatorId) return
    const result:Work = await api('/v1/operators/'+encodeURIComponent(operatorId)+'/work')
    setWork(result)
    const unseen=result.offers.find(offer=>!notified.current.has(offer.offer_id))
    if(unseen){
      notified.current.add(unseen.offer_id)
      setAlertOffer(unseen)
      if(browserAlertsRef.current && 'Notification' in window
          && Notification.permission==='granted'){
        try{
          new Notification('Novo atendimento no Handoff Hub',{
            body:unseen.subject+' · '+unseen.requester_label
          })
        }catch{ /* Some browsers do not support direct notifications. Modal still appears. */ }
      }
    }
    setAlertOffer(current=>current && !result.offers.some(o=>o.offer_id===current.offer_id)
      ? null : current)
  },[operatorId,api])

  useEffect(()=>{
    setSelectedId(null)
    setWork(null)
    setMessages([])
    setNotice('')
    void reload().catch(e=>setError((e as Error).message))
  },[reload])

  useEffect(()=>{
    const poll=()=>{void reload().catch(e=>setError((e as Error).message))}
    const id=window.setInterval(poll,3000)
    return ()=>window.clearInterval(id)
  },[reload])

  useEffect(()=>{
    if(!selectedId) {setMessages([]);setTimeline([]);setTransferNotes([]);return}
    let cancelled=false
    setTransferNotes([])
    Promise.all([
      api('/v1/handoffs/'+selectedId+'/messages'),
      api('/v1/handoffs/'+selectedId+'/timeline'),
    ]).then(([msgs,history]:[ChatMessage[],TimelineResponse])=>{
      if(cancelled)return
      setMessages(msgs)
      setTimeline(history.events.map(e=>e.type+' · '+e.actor))
      setTransferNotes(history.transfers??[])
    }).catch(e=>{if(!cancelled)setError((e as Error).message)})
    return ()=>{cancelled=true}
  },[selectedId,api])

  // Show the previous operator's handoff note before the new operator accepts.
  // A transfer note is INTERNAL metadata, never a message to the end user.
  useEffect(()=>{
    if(!alertOffer){setOfferTransfer(null);return}
    let cancelled=false
    setOfferTransfer(null)
    void api('/v1/handoffs/'+encodeURIComponent(alertOffer.session_id)+'/timeline')
      .then((history:TimelineResponse)=>{
        if(!cancelled)setOfferTransfer(history.transfers?.at(-1)??null)
      })
      .catch(()=>{if(!cancelled)setOfferTransfer(null)})
    return ()=>{cancelled=true}
  },[alertOffer?.session_id,api])

  // Destinations are NOT operator dispatch memberships. Load only for the
  // currently owned conversation and invalidate stale requests on selection changes.
  useEffect(()=>{
    if(!transferOpen || !selectedId){
      setTransferTargets([])
      setTargetQueue('')
      setTransferLoading(false)
      return
    }
    let cancelled=false
    setTransferLoading(true)
    setTransferTargets([])
    setTargetQueue('')
    void api('/v1/handoffs/'+encodeURIComponent(selectedId)+'/transfer-targets')
      .then((result:TransferTargetResponse)=>{
        if(cancelled)return
        const destinations=result.destinations??[]
        setTransferTargets(destinations)
        setTargetQueue(destinations[0]?.id??'')
      })
      .catch(e=>{if(!cancelled)setError((e as Error).message)})
      .finally(()=>{if(!cancelled)setTransferLoading(false)})
    return ()=>{cancelled=true}
  },[api,selectedId,transferOpen])

  // Keep the active conversation fresh independently of offer notifications.
  useEffect(()=>{
    if(!selectedId)return
    let cancelled=false
    const refreshMessages=()=>{
      void api('/v1/handoffs/'+selectedId+'/messages').then((items:ChatMessage[])=>{
        if(!cancelled)setMessages(items)
      }).catch(e=>{if(!cancelled)setError((e as Error).message)})
    }
    const interval=window.setInterval(refreshMessages,3000)
    return ()=>{cancelled=true;window.clearInterval(interval)}
  },[selectedId,api])

  useEffect(()=>{
    if(messagePaneRef.current)messagePaneRef.current.scrollTop=messagePaneRef.current.scrollHeight
  },[selectedId,messages.length])

  async function execute(action:()=>Promise<any>,success:string,select?:string|null) {
    setBusy(true);setError('');setNotice('')
    try{
      const result=await action()
      await reload()
      await onChanged()
      if(select!==undefined){
        setTransferNotes([])
        setTimeline([])
        setSelectedId(select)
        setMobilePanel(select?'chat':'work')
      }
      setTransferOpen(false)
      setNotice(success)
      return result
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  async function sendMessage(sender:'USER'|'OPERATOR') {
    if(!selected)return
    const content=sender==='USER'?'Olá, preciso de ajuda com a solicitação.':reply.trim()
    if(!content)return
    await execute(async()=>{
      await api('/v1/handoffs/'+selected.id+'/messages','POST',{
        sender,content,operator_id:sender==='OPERATOR'?operatorId:undefined,
        external_message_id:crypto.randomUUID(),
      })
      setMessages(await api('/v1/handoffs/'+selected.id+'/messages'))
      if(sender==='OPERATOR')setReply('')
    },sender==='OPERATOR'?'Resposta registrada na outbox local.':'Mensagem de usuário simulada recebida.')
  }

  const offerCount=work?.offers.length??0
  const activeCount=work?.active.length??0

  return <div className="desk-layout desk-layout--compact" data-panel={mobilePanel}>
    {alertOffer && <div className="offer-overlay" role="presentation">
      <div className="offer-dialog" role="alertdialog" aria-modal="true"
        aria-labelledby="offer-dialog-title" aria-describedby="offer-dialog-text">
        <div className="offer-dialog__body" role="region"
          aria-label="Detalhes da oferta" tabIndex={0}>
        <span className="eyebrow">NOVA SOLICITAÇÃO · OFERTA AUTOMÁTICA</span>
        <h2 id="offer-dialog-title">Você recebeu um atendimento</h2>
        <p id="offer-dialog-text"><strong>{alertOffer.requester_label}</strong>
          <span>{alertOffer.subject} · {queueTitle(alertOffer.queue_id)}</span></p>
        {offerTransfer&&<div className="offer-dialog__transfer-note" role="note">
          <strong><ArrowRightLeft size={14}/> Orientação interna da transferência</strong>
          <small>{transferHeading(offerTransfer)} · {transferAuthor(offerTransfer)}</small>
          <p>{offerTransfer.reason}</p>
        </div>}
        <p className="offer-dialog__hint">A oferta expira em até dois minutos. Se não for aceita, retorna à fila.</p>
        </div>
        <div className="offer-dialog__buttons">
          <button className="outline" disabled={busy} onClick={()=>void execute(
            ()=>api('/v1/handoffs/'+alertOffer.session_id+'/decline','POST',{operator_id:operatorId}),
            'Oferta recusada; atendimento devolvido à fila.',null
          )}><XCircle size={16}/> Recusar</button>
          <button ref={acceptButtonRef} className="primary" disabled={busy} onClick={()=>void execute(
            ()=>api('/v1/handoffs/'+alertOffer.session_id+'/accept','POST',{operator_id:operatorId}),
            'Atendimento aceito e iniciado.',alertOffer.session_id
          )}><CheckCircle2 size={16}/> Aceitar atendimento</button>
        </div>
      </div>
    </div>}
    <div className="desk-top">
      <div className="desk-heading">
        <span className="desk-kicker"><Headset size={15}/> CENTRAL DE ATENDIMENTO</span>
        <h3>Mesa do Operador</h3>
      </div>
      <div className="desk-identity">
        {lockedIdentity?<strong>{work?.operator.name??operators.find(o=>o.id===operatorId)?.name??operatorId}</strong>
          :<select aria-label="Operador de demonstração" id="desk-operator" value={operatorId}
            disabled={busy} onChange={e=>setOperatorId(e.target.value)}>
            {operators.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}
          </select>}
        <span className="desk-presence-inline">
          <span className="online-dot"/> Presença
          {lockedIdentity?<select id="self-presence" aria-label="Minha disponibilidade"
            value={work?.operator.presence??'OFFLINE'} disabled={busy}
            onChange={e=>void execute(
              ()=>api('/v1/operators/'+operatorId+'/presence','PATCH',{presence:e.target.value}),
              'Disponibilidade atualizada.'
            )}>
            <option value="AVAILABLE">Disponível</option>
            <option value="AWAY">Em pausa</option>
            <option value="OFFLINE">Indisponível</option>
          </select>:<b>{work?.operator.presence??'OFFLINE'}</b>}
        </span>
        {lockedIdentity&&<button className="outline small desk-notification-button"
          title="Ativar notificações do sistema operacional" disabled={browserAlerts||!('Notification' in window)}
          onClick={async()=>{
            if(!('Notification' in window))return
            const permission=await Notification.requestPermission()
            setBrowserAlerts(permission==='granted')
          }}>{browserAlerts?'Notificações ativas':'Ativar alertas'}</button>}
        <button className="outline small" title="Atualizar atendimento" disabled={busy}
          onClick={()=>void reload()}><RefreshCw size={14}/> <span className="desk-refresh-label">Atualizar</span></button>
      </div>
    </div>
    <div className="desk-feedback" aria-live="polite">
      {error&&<div className="alert" role="alert"><ShieldAlert size={16}/>{error}
        <button onClick={()=>setError('')}>Fechar</button></div>}
      {notice&&<div className="notice" role="status"><CheckCircle2 size={15}/>{notice}
        <button aria-label="Dispensar aviso" onClick={()=>setNotice('')}>×</button></div>}
    </div>
    <div className="desk-mobile-tabs" role="group" aria-label="Painel da Mesa do Operador">
      <button className={mobilePanel==='work'?'selected':''} onClick={()=>setMobilePanel('work')}>
        Atendimentos <span>{offerCount+activeCount}</span>
      </button>
      <button className={mobilePanel==='chat'?'selected':''} onClick={()=>setMobilePanel('chat')}
        disabled={!selectedId}>Conversa</button>
    </div>
    <div className="desk-grid">
      <section className="panel desk-inbox">
        <div className="panel-header desk-worklist-head"><h3>Meus atendimentos</h3>
          <span>{activeCount} ativo(s) · {offerCount} oferta(s)</span></div>
        <div className="desk-worklist" role="region" aria-label="Ofertas e atendimentos">
        <div className="desk-block-header">OFERTAS PENDENTES <span>{offerCount}</span></div>
        {!offerCount&&<div className="desk-empty desk-empty--compact"><Clock3 size={15}/>
          <span>Aguardando novas ofertas</span>{!lockedIdentity&&<button className="outline small"
            onClick={onGoQueues}>Filas</button>}</div>}
        {work?.offers.map(o=><div className="desk-item" key={o.offer_id}>
          <span className="desk-item-meta">OFERTA · {queueTitle(o.queue_id)}</span>
          <b>{o.requester_label}</b><p>{o.subject}</p>
          <small>Validade: {labelTime(o.expires_at)}</small>
          <div className="desk-actions">
            <button className="primary small" disabled={busy} onClick={()=>void execute(
              ()=>api('/v1/handoffs/'+o.session_id+'/accept','POST',{operator_id:operatorId}),
              'Oferta aceita. Atendimento iniciado.',o.session_id
            )}><CheckCircle2 size={14}/> Aceitar</button>
            <button className="outline small" disabled={busy} onClick={()=>void execute(
              ()=>api('/v1/handoffs/'+o.session_id+'/decline','POST',{operator_id:operatorId}),
              'Oferta recusada e devolvida à fila.',null
            )}><XCircle size={14}/> Recusar</button>
          </div>
        </div>)}
        <div className="desk-block-header">EM ATENDIMENTO <span>{activeCount}</span></div>
        {!activeCount&&<div className="desk-empty desk-empty--small">Nenhum atendimento ativo para este operador.</div>}
        {work?.active.map(h=><button className={'desk-active '+(selectedId===h.id?'desk-active--selected':'')}
          key={h.id} onClick={()=>{setTransferOpen(false);setTransferNotes([]);setTimeline([]);setSelectedId(h.id);setMobilePanel('chat')}}>
          <div className="avatar">{h.requester_label.slice(0,2).toUpperCase()}</div>
          <div><b>{h.requester_label}</b><p>{h.subject}</p><small>{queueTitle(h.queue_id)}</small></div>
          <MessageSquareText size={17}/>
        </button>)}
        </div>
      </section>
      <section className="panel desk-chat">
        {selected?<><div className="conversation-head"><div className="avatar">OP</div>
          <div className="desk-chat-identity"><b>{selected.requester_label}</b>
            <p>{selected.subject} · {queueTitle(selected.queue_id)}</p></div>
          <div className="desk-chat-tools">
            <button className="outline small" disabled={busy} aria-expanded={auditOpen}
              onClick={()=>setAuditOpen(value=>!value)}>Histórico</button>
            <button className="outline small" disabled={busy} aria-expanded={transferOpen}
              onClick={()=>{setTransferOpen(value=>!value);setAuditOpen(false)}}>
              <ArrowRightLeft size={14}/> Transferir</button>
            <button className="primary small" disabled={busy} onClick={()=>void execute(
              ()=>api('/v1/operators/'+operatorId+'/handoffs/'+selected.id+'/close','POST'),
              'Atendimento encerrado.',null
            )}><CheckCircle2 size={14}/> Encerrar</button>
          </div>
        </div>
        {transferOpen&&<div className="desk-transfer-panel" role="region"
          aria-label="Transferência de atendimento">
          <label htmlFor="transfer-destination">Fila de destino</label>
          <select id="transfer-destination" value={targetQueue}
            disabled={busy||transferLoading||transferTargets.length===0}
            onChange={e=>setTargetQueue(e.target.value)}>
            {transferLoading?<option value="">Carregando destinos...</option>
              :transferTargets.length===0?<option value="">Nenhuma fila disponível</option>
              :transferTargets.map(q=><option value={q.id} key={q.id}>{q.name}</option>)}
          </select>
          <input value={transferReason} onChange={e=>setTransferReason(e.target.value)}
            maxLength={300} aria-label="Motivo da transferência" placeholder="Motivo da transferência"/>
          <button className="primary small"
            disabled={busy||transferLoading||!transferTargets.some(q=>q.id===targetQueue)
              ||transferReason.trim().length<3}
            onClick={()=>void execute(
              ()=>api('/v1/handoffs/'+selected.id+'/transfer','POST',{
                operator_id:operatorId,queue_id:targetQueue,reason:transferReason.trim(),
              }), 'Atendimento transferido para '+queueTitle(targetQueue)+'.',null
            )}>Confirmar transferência</button>
        </div>}
        {auditOpen&&<div className="desk-audit-panel">
          <b>Histórico auditável</b>
          <span>{timeline.slice(-6).join('  •  ') || 'Aguardando eventos'}</span>
          {transferNotes.length>0&&<div className="desk-audit-transfers">
            {transferNotes.map((note,i)=><p key={note.at+'-'+i}>
              <strong>{transferHeading(note)} · {transferAuthor(note)}:</strong> {note.reason}
            </p>)}
          </div>}
        </div>}
        <div className="desk-chat-list" ref={messagePaneRef}>
          {latestTransfer&&<div className="desk-handoff-note" role="note">
            <strong><ArrowRightLeft size={14}/> Orientação interna recebida</strong>
            <small>{transferHeading(latestTransfer)} · {transferAuthor(latestTransfer)}
              {' · '}{labelTime(latestTransfer.at)}</small>
            <p>{latestTransfer.reason}</p>
            <span>Nota de transferência — não enviada ao usuário final</span>
          </div>}
          <div className="chat-notice">CONVERSA SIMULADA · NÃO ENVIADA AO TEAMS</div>
          {!messages.length&&<div className="empty">Nenhuma mensagem registrada nesta conversa.</div>}
          {messages.map(m=><div key={m.id} className={'bubble-row '+(m.sender==='OPERATOR'?'right':'')}>
            <div className="bubble"><b>{m.sender==='OPERATOR'?'Operador':'Usuário'}</b><p>{m.content}</p><small>{labelTime(m.created_at)}</small></div>
          </div>)}
        </div>
        <div className="desk-compose">
          <textarea value={reply} onChange={e=>setReply(e.target.value)} rows={2}
            onKeyDown={e=>{
              if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){
                e.preventDefault()
                if(!busy&&reply.trim())void sendMessage('OPERATOR')
              }
            }}
            maxLength={4000} placeholder="Responder... Enter envia · Shift+Enter quebra linha"
            aria-label="Responder como operador"/>
          <div className="desk-actions">
            {!lockedIdentity&&<button className="outline small" disabled={busy} onClick={()=>void sendMessage('USER')}>Simular usuário</button>}
            <button className="primary small" disabled={busy||!reply.trim()} onClick={()=>void sendMessage('OPERATOR')}><Send size={14}/> Enviar resposta</button>
          </div>
        </div>
        </>:<div className="center-empty"><Inbox size={38}/><h3>Selecione um atendimento ativo</h3>
          <p>Ao aceitar uma oferta, a conversa aparece aqui com as opções de resposta, transferência e encerramento.</p></div>}
      </section>
    </div>
  </div>
}
