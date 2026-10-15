import { useCallback, useEffect, useRef, useState } from 'react'
import GuidedDemo, { type JourneyStage } from './GuidedDemo'
import {
  Activity, ArrowRight, CheckCircle2, CircleHelp, ClipboardList, Headset,
  Inbox, Layers, Lock, MessageSquareText, Plus, RefreshCw, Send,
  Server, ShieldCheck, UserRoundCheck, Users
} from 'lucide-react'

type Ticket = {
  id: string; operation_id: string; integration_id: string; queue_id: string
  requester_label: string; subject: string; status: string; operator_id: string | null
  created_at: string
}
type Queue = {id: string; name: string; waiting: number}
type Operator = {id: string; name: string; presence: string; capacity: number; active: number}
type Message = {id: string; sender: string; content: string; created_at: string}
type DashboardSnapshot = {
  handoffs: Ticket[]; queues: Queue[]; operators: Operator[]
  outbox: {total: number; pending: number}
}
const API = 'http://127.0.0.1:8000'
const time = (iso: string) => new Date(iso).toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'})
const initials = (name: string) => name.split(' ').slice(0,2).map(x => x[0]).join('').toUpperCase()

export default function App() {
  const [key, setKey] = useState('')
  const [connected, setConnected] = useState(false)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [queues, setQueues] = useState<Queue[]>([])
  const [operators, setOperators] = useState<Operator[]>([])
  const [delivery, setDelivery] = useState({total:0, pending:0})
  const [filter, setFilter] = useState<'all'|'active'|'queued'|'closed'>('all')
  const [messages, setMessages] = useState<Message[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const replyRef = useRef<HTMLTextAreaElement>(null)
  const chatListRef = useRef<HTMLDivElement>(null)
  const [busy, setBusy] = useState(false)
  const [view, setView] = useState<'inbox'|'queues'|'operators'>('inbox')
  const selected = tickets.find(t => t.id === selectedId)
  const visibleTickets = tickets.filter(t => filter==='all' || t.status.toLowerCase()===filter)
  const stage: JourneyStage = !selected ? 'create'
    : selected.status === 'QUEUED' ? 'assign'
    : selected.status === 'CLOSED' ? 'done'
    : !messages.some(m => m.sender === 'USER') ? 'receive'
    : !messages.some(m => m.sender === 'OPERATOR') ? 'reply'
    : 'close'
  const selectTicket = (id: string) => { setMessages([]); setSelectedId(id); setView('inbox'); }

  const api = useCallback(async (path: string, method='GET', body?: object, extra?: Record<string,string>) => {
    const response = await fetch(API+path, {
      method, headers:{'X-POC-Key':key,'Content-Type':'application/json',...(extra||{})},
      body:body ? JSON.stringify(body) : undefined
    })
    if (!response.ok) throw new Error(String(response.status)+': '+(await response.text()).slice(0,220))
    return response.json()
  }, [key])

  const refresh = useCallback(async () => {
    if (!connected) return
    try {
      const snapshot: DashboardSnapshot = await api('/v1/dashboard')
      setTickets(snapshot.handoffs)
      setQueues(snapshot.queues)
      setOperators(snapshot.operators)
      setDelivery(snapshot.outbox)
      if (view==='inbox' && selectedId) {
        setMessages(await api('/v1/handoffs/'+selectedId+'/messages'))
      }
    } catch(e) {setError((e as Error).message)}
  }, [connected,selectedId,view,api])

  useEffect(() => {
    if (!connected) return
    const tick = () => { if (document.visibilityState==='visible') void refresh() }
    const interval = window.setInterval(tick,15000)
    document.addEventListener('visibilitychange',tick)
    return () => {window.clearInterval(interval);document.removeEventListener('visibilitychange',tick)}
  },[refresh,connected])
  useEffect(() => {
    if (!connected || !selectedId) {setMessages([]);return}
    void api('/v1/handoffs/'+selectedId+'/messages').then(setMessages).catch(e => setError(e.message))
  },[connected,selectedId,api])

  useEffect(() => {
    if (view!=='inbox' || !chatListRef.current) return
    chatListRef.current.scrollTop = chatListRef.current.scrollHeight
  }, [messages.length,selectedId,view])

  async function run(fn:()=>Promise<unknown>) {
    setBusy(true);setError('');setNotice('')
    try {await fn();await refresh()} catch(e) {setError((e as Error).message)}
    finally {setBusy(false)}
  }
  async function connect() {
    setBusy(true);setError('')
    try {
      await api('/v1/demo/bootstrap','POST')
      const snapshot: DashboardSnapshot = await api('/v1/dashboard')
      setTickets(snapshot.handoffs);setQueues(snapshot.queues)
      setOperators(snapshot.operators);setDelivery(snapshot.outbox);setConnected(true)
    } catch(e) {setError((e as Error).message)}
    finally {setBusy(false)}
  }
  const waiting=tickets.filter(t => t.status==='QUEUED').length
  const active=tickets.filter(t => t.status==='ACTIVE').length
  const free=operators.filter(o=>o.presence==='AVAILABLE'&&o.active<o.capacity).length

  async function createTicket() {
    const id=crypto.randomUUID()
    await run(async () => {
      const item=await api('/v1/handoffs','POST',{
        external_conversation_id:'demo-'+id,requester_label:'Usuário simulado '+(tickets.length+1),
        subject:['Solicitação de acesso','Ajuda com aplicativo','Equipamento indisponível'][tickets.length%3]
      },{'Idempotency-Key':id})
      selectTicket(item.id)
      setFilter('all')
      setNotice('Solicitação criada. Agora distribua o próximo atendimento da fila.')
    })
  }

  async function dispatchNext() {
    await run(async () => {
      const result = await api('/v1/dispatch/next','POST',{})
      if (result.result === 'assigned') {
        selectTicket(result.session.id)
        setFilter('all')
        setNotice('Atendimento atribuído. Agora simule uma mensagem do usuário.')
      } else if (result.result === 'no_operator_available') {
        setNotice('Não há operadores disponíveis. Confira o status na seção Operadores.')
      } else {
        setNotice('Fila vazia. Crie uma solicitação de teste primeiro.')
      }
    })
  }

  function focusReply() {
    if (!draft.trim()) setDraft('Olá! Recebi sua solicitação e vou ajudar a resolver.')
    replyRef.current?.focus()
  }

  async function closeSelected() {
    if (!selected) return
    await run(async () => {
      await api('/v1/handoffs/'+selected.id+'/close','POST')
      setNotice('Atendimento encerrado. A capacidade do operador foi liberada.')
    })
  }

  async function send(sender:'USER'|'OPERATOR') {
    if (!selected || (sender==='OPERATOR'&&!draft.trim())) return
    const content=sender==='USER'?'Olá! Poderia me auxiliar com meu acesso?':draft.trim()
    const handoffId=selected.id
    await run(async () => {
      await api('/v1/handoffs/'+handoffId+'/messages','POST',{
        sender,content,external_message_id:crypto.randomUUID()
      })
      setMessages(await api('/v1/handoffs/'+handoffId+'/messages'))
      if (sender==='OPERATOR') {
        setDraft('')
        setNotice('Resposta registrada na outbox. Nenhuma mensagem foi enviada ao Teams.')
      } else {
        setNotice('Mensagem fictícia recebida. Responda como operador.')
      }
    })
  }

  if (!connected) return <div className="login-wrap"><section className="login-panel">
    <div className="app-mark"><Headset size={26}/></div>
    <div className="kicker">HANDOFF HUB · SQLITE POC</div>
    <h1>Central de atendimento independente.</h1>
    <p>Experimente a gestão de filas, operadores e conversas em ambiente local. Nenhuma mensagem é enviada ao Teams.</p>
    <label htmlFor="poc-key">Chave local configurada no backend</label>
    <input id="poc-key" type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)}
      placeholder="HANDOFF_POC_KEY" onKeyDown={e=>{if(e.key==='Enter')void connect()}}/>
    <button className="primary full" disabled={!key||busy} onClick={()=>void connect()}><Lock size={16}/> Entrar na POC <ArrowRight size={16}/></button>
    {error&&<p className="alert">{error}</p>}
    <small>Chave armazenada apenas na memória desta aba.</small>
  </section></div>

  return <div className="layout">
    <aside className="sidebar">
      <div className="brand"><div className="app-mark"><Headset size={20}/></div><div><b>Handoff Hub</b><small>CONTROL CENTER</small></div></div>
      <span className="sidebar-title">WORKSPACE</span>
      <button className={'nav '+(view==='inbox'?'active':'')} onClick={()=>{setView('inbox');setNotice('')}}><Inbox size={18}/> Conversas <em>{tickets.length}</em></button>
      <button className={'nav '+(view==='queues'?'active':'')} onClick={()=>{setView('queues');setNotice('')}}><Layers size={18}/> Filas <em>{waiting}</em></button>
      <button className={'nav '+(view==='operators'?'active':'')} onClick={()=>{setView('operators');setNotice('')}}><Users size={18}/> Operadores</button>
      <div className="sidebar-bottom"><span className="online-dot"/> API local · SQLite <small>POC 0.2.0 · sem Teams</small></div>
    </aside>
    <main className="content">
      <header className="topbar"><div><span className="kicker">OPERAÇÃO DEMONSTRATIVA</span>
        <h2>{view==='inbox'?'Central de atendimento':view==='queues'?'Gestão de filas':'Equipe de operadores'}</h2></div>
        <div className="top-actions"><span className="local-tag"><ShieldCheck size={15}/> AMBIENTE LOCAL</span>
          <button className="icon-btn" aria-label="Atualizar" onClick={()=>void refresh()}><RefreshCw size={17}/></button></div></header>
      {error&&<div className="alert" role="alert"><CircleHelp size={17}/>{error}<button onClick={()=>setError('')}>Fechar</button></div>}
      {notice&&<div className="notice" role="status"><CheckCircle2 size={16}/><span>{notice}</span><button onClick={()=>setNotice('')} aria-label="Dispensar aviso">×</button></div>}
      {view==='inbox'&&<GuidedDemo
        stage={stage}
        busy={busy}
        hasWaiting={waiting>0}
        availableOperators={free}
        onCreate={()=>void createTicket()}
        onAssign={()=>void dispatchNext()}
        onSimulateUser={()=>void send('USER')}
        onFocusReply={focusReply}
        onClose={()=>void closeSelected()}
      />}
      <div className="metrics">
        {[
          {name:'Em atendimento',value:active,detail:'Conversas em andamento',icon:<MessageSquareText/>},
          {name:'Aguardando',value:waiting,detail:'Solicitações em fila',icon:<ClipboardList/>},
          {name:'Operadores livres',value:free,detail:'Capacidade disponível',icon:<UserRoundCheck/>},
          {name:'Sem envio externo',value:delivery.pending,detail:'Respostas aguardando conector',icon:<Activity/>}
        ].map(m=><div className="metric" key={m.name}><div className="metric-name">{m.name}<span>{m.icon}</span></div>
          <strong>{m.value}</strong><small>{m.detail}</small></div>)}
      </div>
      {view==='inbox'&&<div className="workspace">
        <section className="panel sessions"><div className="panel-header"><div><h3>Conversas</h3><p>Atendimentos registrados</p></div>
          <button className="primary small" disabled={busy} onClick={()=>void createTicket()}><Plus size={14}/> Nova solicitação</button></div>
          <div className="tabs" role="group" aria-label="Filtrar conversas">
            <button type="button" className={filter==='all'?'current':''} aria-pressed={filter==='all'} onClick={()=>setFilter('all')}>Todas <b>{tickets.length}</b></button>
            <button type="button" className={filter==='active'?'current':''} aria-pressed={filter==='active'} onClick={()=>setFilter('active')}>Em atendimento <b>{active}</b></button>
            <button type="button" className={filter==='queued'?'current':''} aria-pressed={filter==='queued'} onClick={()=>setFilter('queued')}>Na fila <b>{waiting}</b></button>
            <button type="button" className={filter==='closed'?'current':''} aria-pressed={filter==='closed'} onClick={()=>setFilter('closed')}>Encerradas <b>{tickets.filter(t=>t.status==='CLOSED').length}</b></button>
          </div>
          <div className="sessions-scroll">{tickets.length===0&&<div className="empty empty--help"><MessageSquareText size={27}/><strong>Sua primeira conversa começa aqui</strong><p>Crie uma solicitação fictícia para experimentar a fila e o atendimento.</p><button className="primary small" disabled={busy} onClick={()=>void createTicket()}>Criar solicitação</button></div>}
            {tickets.length>0 && visibleTickets.length===0 && <p className="empty">Nenhuma conversa nesta categoria.</p>}
            {visibleTickets.map(t=><button key={t.id} onClick={()=>selectTicket(t.id)} className={'session '+(t.id===selectedId?'selected':'')}>
              <div className="avatar">{initials(t.requester_label)}</div><div className="session-info">
                <div className="session-title"><b>{t.requester_label}</b><small>{time(t.created_at)}</small></div>
                <p>{t.subject}</p><div className="session-meta"><span className={'status '+t.status.toLowerCase()}>{t.status==='QUEUED'?'Na fila':t.status==='ACTIVE'?'Ativo':'Encerrado'}</span><small>{t.queue_id.toUpperCase()}</small></div>
              </div></button>)}</div></section>
        <section className="panel conversation">{selected?<><div className="conversation-head"><div className="avatar">{initials(selected.requester_label)}</div>
          <div><b>{selected.requester_label}</b><p>{selected.subject} · {selected.integration_id}</p></div><span className={'status '+selected.status.toLowerCase()}>{selected.status}</span></div>
          <div className="context"><Server size={15}/> Sessão {selected.id.slice(0,8)} · {selected.operator_id||'Aguardando operador'}</div>
          <div className={'context-hint context-hint--'+selected.status.toLowerCase()}>
            {selected.status==='QUEUED'?<>
              <div><strong>Aguardando distribuição</strong><p>A solicitação entrou na fila. Distribua o próximo atendimento para iniciar a conversa.</p></div>
              <button className="primary small" disabled={busy||free===0} onClick={()=>void dispatchNext()}>Distribuir próximo da fila <ArrowRight size={14}/></button>
            </>:selected.status==='ACTIVE' && !messages.some(m=>m.sender==='USER')?<>
              <div><strong>Operador atribuído</strong><p>Agora simule o recebimento de uma mensagem para testar a resposta humana.</p></div>
              <button className="primary small" disabled={busy} onClick={()=>void send('USER')}>Receber mensagem de teste <ArrowRight size={14}/></button>
            </>:selected.status==='CLOSED'?<div><strong>Atendimento encerrado</strong><p>O operador está livre para receber outra solicitação.</p></div>:null}
          </div>
          <div className="chat-list" ref={chatListRef}><div className="chat-notice">SIMULAÇÃO LOCAL · NÃO ENVIADA AO TEAMS</div>
            {!messages.length&&<div className="empty">Nenhuma mensagem nesta conversa.</div>}
            {messages.map(m=><div key={m.id} className={'bubble-row '+(m.sender==='OPERATOR'?'right':'')}><div className="bubble"><b>{m.sender==='OPERATOR'?'Operador':'Usuário simulado'}</b><p>{m.content}</p><small>{time(m.created_at)}</small></div></div>)}
          </div><div className="composer"><div className="composer-hint">Sua resposta como operador será registrada na outbox, sem envio ao Teams.</div><textarea ref={replyRef} aria-label="Resposta do operador" value={draft} onChange={e=>setDraft(e.target.value)}
            disabled={selected.status!=='ACTIVE'} placeholder="Escreva uma mensagem..." rows={2}/>
            <div className="composer-actions"><button className="outline" disabled={busy||selected.status==='CLOSED'} onClick={()=>void send('USER')}><Plus size={13}/> Mensagem de teste</button>
              <button className="outline" disabled={busy||selected.status!=='ACTIVE'} onClick={()=>void closeSelected()}><CheckCircle2 size={13}/> Encerrar</button>
              <button className="primary" disabled={busy||selected.status!=='ACTIVE'||!draft.trim()} onClick={()=>void send('OPERATOR')}>Enviar resposta <Send size={14}/></button></div>
          </div></>:<div className="center-empty"><MessageSquareText size={38}/><h3>Inicie um atendimento de teste</h3><p>Primeiro, crie uma solicitação. Depois distribua, converse e encerre — tudo pela interface.</p><button className="primary" disabled={busy} onClick={()=>void createTicket()}><Plus size={15}/> Criar primeira solicitação</button></div>}</section>
        <aside className="side-panels"><section className="panel widget"><h3>Distribuição</h3><p>Fila por ordem de chegada e reserva transacional.</p>
          <button className="primary full" disabled={busy||!waiting} onClick={()=>void dispatchNext()}><UserRoundCheck size={15}/> Distribuir próximo da fila</button>
          <h4>Filas acompanhadas</h4>{queues.map(q=><div className="line" key={q.id}><span>{q.name}</span><b>{q.waiting}</b></div>)}</section>
          <section className="panel widget"><h3>Integrações</h3><div className="line"><span>Backend local</span><b className="good">Online</b></div>
            <div className="line"><span>Teams adapter</span><b>Não instalado</b></div>
            <div className="line"><span>Respostas sem envio</span><b>{delivery.pending} de {delivery.total}</b></div></section></aside>
      </div>}
      {view==='queues'&&<section className="panel list-panel"><div className="panel-header"><div><h3>Filas configuradas</h3><p>Distribuição SQLite</p></div>
        <button className="primary small" disabled={busy||!waiting} onClick={()=>void dispatchNext()}>Distribuir próximo da fila <ArrowRight size={14}/></button></div>
        {queues.map(q=><div className="record" key={q.id}><div className="record-icon"><Layers size={20}/></div><div><b>{q.name}</b><p>Operação demonstrativa · {q.id}</p></div><span className="pill">{q.waiting} aguardando</span></div>)}</section>}
      {view==='operators'&&<section className="panel list-panel"><div className="panel-header"><div><h3>Operadores</h3><p>Capacidade e presença</p></div></div>
        {operators.map(o=><div className="record" key={o.id}><div className="avatar">{initials(o.name)}</div><div className="fill"><b>{o.name}</b><p>{o.active} de {o.capacity} atendimento(s)</p></div>
          <select aria-label={'Presença de '+o.name} value={o.presence} disabled={busy} onChange={e=>void run(()=>api('/v1/operators/'+o.id+'/presence','PATCH',{presence:e.target.value}))}>
            <option value="AVAILABLE">Disponível</option><option value="AWAY">Em pausa</option><option value="OFFLINE">Offline</option>
          </select></div>)}</section>}
      <footer>Handoff Hub · SQLite POC · Sem autenticação corporativa · Uso local de desenvolvimento</footer>
    </main>
  </div>
}
