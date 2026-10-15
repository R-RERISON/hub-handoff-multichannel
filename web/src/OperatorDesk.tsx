import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRightLeft, CheckCircle2, Clock3, Headset, Inbox, MessageSquareText,
  RefreshCw, Send, ShieldAlert, UserRoundCheck, XCircle
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
type Api = (path: string, method?: string, body?: object, extra?: Record<string,string>)=>Promise<any>
type Props = {
  operators: Operator[]
  queues: Queue[]
  preferredOperatorId: string
  api: Api
  onChanged: ()=>Promise<void>
  onGoQueues: ()=>void
}

const labelTime=(value:string)=>new Date(value).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})

export default function OperatorDesk({operators,queues,preferredOperatorId,api,onChanged,onGoQueues}:Props) {
  const [operatorId,setOperatorId] = useState(preferredOperatorId)
  const [work,setWork] = useState<Work|null>(null)
  const [selectedId,setSelectedId] = useState<string|null>(null)
  const [messages,setMessages] = useState<ChatMessage[]>([])
  const [reply,setReply] = useState('')
  const [targetQueue,setTargetQueue] = useState('n2')
  const [transferReason,setTransferReason] = useState('Encaminhamento para a equipe especializada')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [timeline,setTimeline] = useState<string[]>([])
  const selected = work?.active.find(h=>h.id===selectedId) ?? null
  const queueTitle = (id:string) => queues.find(q=>q.id===id)?.name ?? id

  useEffect(()=>setOperatorId(preferredOperatorId),[preferredOperatorId])

  const reload = useCallback(async () => {
    if (!operatorId) return
    const result:Work = await api('/v1/operators/'+encodeURIComponent(operatorId)+'/work')
    setWork(result)
  },[operatorId,api])

  useEffect(()=>{
    setSelectedId(null)
    setWork(null)
    setMessages([])
    setNotice('')
    void reload().catch(e=>setError((e as Error).message))
  },[reload])

  useEffect(()=>{
    const poll=()=>{if(document.visibilityState==='visible')void reload().catch(e=>setError((e as Error).message))}
    const id=window.setInterval(poll,15000)
    return ()=>window.clearInterval(id)
  },[reload])

  useEffect(()=>{
    if(!selectedId) {setMessages([]);setTimeline([]);return}
    let cancelled=false
    Promise.all([
      api('/v1/handoffs/'+selectedId+'/messages'),
      api('/v1/handoffs/'+selectedId+'/timeline'),
    ]).then(([msgs,history])=>{
      if(cancelled)return
      setMessages(msgs)
      setTimeline((history.events as {type:string;actor:string}[]).map(e=>e.type+' · '+e.actor))
    }).catch(e=>{if(!cancelled)setError((e as Error).message)})
    return ()=>{cancelled=true}
  },[selectedId,api])

  async function execute(action:()=>Promise<any>,success:string,select?:string|null) {
    setBusy(true);setError('');setNotice('')
    try{
      const result=await action()
      await reload()
      await onChanged()
      if(select!==undefined)setSelectedId(select)
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

  return <div className="desk-layout">
    <div className="desk-top">
      <div>
        <div className="desk-kicker"><Headset size={15}/> WORKSPACE INDEPENDENTE DO OPERADOR</div>
        <h3>Mesa de atendimento</h3>
        <p>Receba ofertas, assuma conversas e transfira atendimentos. Simulação local sem Teams.</p>
      </div>
      <div className="desk-identity">
        <label htmlFor="desk-operator">Operador em demonstração</label>
        <select id="desk-operator" value={operatorId} disabled={busy}
          onChange={e=>setOperatorId(e.target.value)}>
          {operators.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
        <small>Identidade simulada, sem login corporativo</small>
      </div>
    </div>
    {error&&<div className="alert" role="alert"><ShieldAlert size={17}/>{error}<button onClick={()=>setError('')}>Fechar</button></div>}
    {notice&&<div className="notice" role="status"><CheckCircle2 size={16}/>{notice}<button onClick={()=>setNotice('')}>×</button></div>}
    <div className="desk-overview">
      <div><span><Inbox size={16}/> Ofertas recebidas</span><strong>{offerCount}</strong></div>
      <div><span><MessageSquareText size={16}/> Em andamento</span><strong>{activeCount}</strong></div>
      <div><span><UserRoundCheck size={16}/> Presença</span><strong className="desk-presence">{work?.operator.presence==='AVAILABLE'?'Disponível':work?.operator.presence==='AWAY'?'Em pausa':'Offline'}</strong></div>
      <button className="outline" disabled={busy} onClick={()=>void reload()}><RefreshCw size={15}/> Atualizar</button>
    </div>
    <div className="desk-grid">
      <section className="panel desk-inbox">
        <div className="panel-header"><div><h3>Caixa de trabalho</h3><p>Ofertas e atendimentos da identidade selecionada</p></div></div>
        <div className="desk-block-header">OFERTAS PENDENTES <span>{offerCount}</span></div>
        {!offerCount&&<div className="desk-empty"><Clock3 size={23}/><b>Nenhuma oferta aguardando</b><p>A supervisão distribui a próxima solicitação na página Filas.</p><button className="outline" onClick={onGoQueues}>Ir para Filas</button></div>}
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
          key={h.id} onClick={()=>setSelectedId(h.id)}>
          <div className="avatar">{h.requester_label.slice(0,2).toUpperCase()}</div>
          <div><b>{h.requester_label}</b><p>{h.subject}</p><small>{queueTitle(h.queue_id)}</small></div>
          <MessageSquareText size={17}/>
        </button>)}
      </section>
      <section className="panel desk-chat">
        {selected?<><div className="conversation-head"><div className="avatar">OP</div>
          <div><b>{selected.requester_label}</b><p>{selected.subject} · {queueTitle(selected.queue_id)}</p></div>
          <span className="status active">Ativo</span>
        </div>
        <div className="desk-chat-list">
          <div className="chat-notice">CONVERSA SIMULADA · NÃO ENVIADA AO TEAMS</div>
          {!messages.length&&<div className="empty">Nenhuma mensagem. Simule um usuário para começar.</div>}
          {messages.map(m=><div key={m.id} className={'bubble-row '+(m.sender==='OPERATOR'?'right':'')}>
            <div className="bubble"><b>{m.sender==='OPERATOR'?'Operador':'Usuário'}</b><p>{m.content}</p><small>{labelTime(m.created_at)}</small></div>
          </div>)}
        </div>
        <div className="desk-compose">
          <textarea value={reply} onChange={e=>setReply(e.target.value)} rows={2}
            maxLength={4000} placeholder="Escreva sua resposta para o usuário simulado" aria-label="Responder como operador"/>
          <div className="desk-actions">
            <button className="outline small" disabled={busy} onClick={()=>void sendMessage('USER')}>Simular usuário</button>
            <button className="primary small" disabled={busy||!reply.trim()} onClick={()=>void sendMessage('OPERATOR')}><Send size={14}/> Enviar resposta</button>
          </div>
        </div>
        <div className="desk-footer-actions">
          <div className="desk-transfer">
            <label htmlFor="transfer-destination">Transferir atendimento para</label>
            <select id="transfer-destination" value={targetQueue} onChange={e=>setTargetQueue(e.target.value)}>
              {queues.map(q=><option value={q.id} key={q.id}>{q.name}</option>)}
            </select>
            <input value={transferReason} onChange={e=>setTransferReason(e.target.value)}
              maxLength={300} aria-label="Motivo da transferência" placeholder="Motivo da transferência"/>
            <button className="outline small" disabled={busy||transferReason.trim().length<3}
              onClick={()=>void execute(
                ()=>api('/v1/handoffs/'+selected.id+'/transfer','POST',{
                  operator_id:operatorId,queue_id:targetQueue,reason:transferReason.trim(),
                }), 'Atendimento transferido e devolvido à fila.',null
              )}><ArrowRightLeft size={14}/> Transferir</button>
          </div>
          <button className="primary small" disabled={busy} onClick={()=>void execute(
            ()=>api('/v1/operators/'+operatorId+'/handoffs/'+selected.id+'/close','POST'),
            'Atendimento concluído e capacidade liberada.',null
          )}><CheckCircle2 size={14}/> Encerrar atendimento</button>
        </div>
        <div className="desk-timeline"><b>Histórico auditável</b><span>{timeline.slice(-4).join('  •  ') || 'Aguardando eventos'}</span></div>
        </>:<div className="center-empty"><Inbox size={38}/><h3>Selecione um atendimento ativo</h3>
          <p>Ao aceitar uma oferta, a conversa aparece aqui com as opções de resposta, transferência e encerramento.</p></div>}
      </section>
    </div>
  </div>
}
