import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  ArrowLeftRight, ArrowRight, ChartNoAxesCombined,
  CheckCircle2, FlaskConical, Headset, Layers, Lock,
  MessageSquareText, RefreshCw, Settings2, ShieldCheck, Users
} from 'lucide-react'
import OperatorDesk from './OperatorDesk'
import AdminLanding from './workspaces/AdminLanding'
import DemoLab from './workspaces/DemoLab'
import SupervisorConversations from './workspaces/SupervisorConversations'
import SupervisorOverview from './workspaces/SupervisorOverview'
import SupervisorQueues from './workspaces/SupervisorQueues'
import SupervisorTeam from './workspaces/SupervisorTeam'
import type { Api, DashboardSnapshot } from './workspaces/types'

const API_URL = 'http://127.0.0.1:8000'
const EMPTY_SNAPSHOT: DashboardSnapshot = {
  handoffs: [], queues: [], operators: [], outbox: { total: 0, pending: 0 },
}

function Logo() {
  return <div className="brand">
    <div className="app-mark"><Headset size={20}/></div>
    <div><b>Handoff Hub</b><small>MULTICHANNEL PLATFORM</small></div>
  </div>
}

function ActiveLink({to,icon,label,count}:{
  to:string;icon:ReactNode;label:string;count?:number
}) {
  return <NavLink to={to} end={to==='/supervisao'} className={({isActive})=>'nav '+(isActive?'active':'')}>
    {icon}<span>{label}</span>
    {count!==undefined&&<em>{count}</em>}
  </NavLink>
}

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const [key,setKey] = useState('')
  const [connected,setConnected] = useState(false)
  const [snapshot,setSnapshot] = useState<DashboardSnapshot>(EMPTY_SNAPSHOT)
  const [operatorId,setOperatorId] = useState('op-ana')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const operatorMode = location.pathname.startsWith('/operador')
  const adminMode = location.pathname.startsWith('/administracao')
  const offered = snapshot.handoffs.filter(t=>t.status==='OFFERED').length
  const waiting = snapshot.queues.reduce((sum,q)=>sum+q.waiting,0)

  const api:Api = useCallback(async (
    path:string,method='GET',body?:object,extra?:Record<string,string>
  )=>{
    const response = await fetch(API_URL+path, {
      method,
      headers: {'X-POC-Key':key,'Content-Type':'application/json',...(extra||{})},
      body: body ? JSON.stringify(body) : undefined,
    })
    if(!response.ok)throw new Error(String(response.status)+': '+(await response.text()).slice(0,240))
    return response.json()
  },[key])

  const refresh = useCallback(async ()=>{
    if(!connected)return
    try {
      const data:DashboardSnapshot = await api('/v1/dashboard')
      setSnapshot(data)
    }catch(e){setError((e as Error).message)}
  },[connected,api])

  useEffect(()=>{
    if(!connected)return
    const tick = ()=>{if(document.visibilityState==='visible')void refresh()}
    const id = window.setInterval(tick,15000)
    document.addEventListener('visibilitychange',tick)
    return ()=>{
      window.clearInterval(id)
      document.removeEventListener('visibilitychange',tick)
    }
  },[connected,refresh])

  useEffect(()=>{
    setError('')
    setNotice('')
  },[location.pathname])

  async function connect(){
    setBusy(true);setError('')
    try{
      await api('/v1/demo/bootstrap','POST')
      const data:DashboardSnapshot=await api('/v1/dashboard')
      setSnapshot(data);setConnected(true)
      if(location.pathname==='/')navigate('/supervisao',{replace:true})
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  async function createTicket(){
    setBusy(true);setError('');setNotice('')
    try{
      const id=crypto.randomUUID()
      const previous=snapshot.handoffs.length
      await api('/v1/handoffs','POST',{
        external_conversation_id:'demo-'+id,
        requester_label:'Usuário simulado '+(previous+1),
        subject:['Solicitação de acesso','Ajuda com aplicativo','Equipamento indisponível'][previous%3],
      },{'Idempotency-Key':id})
      await refresh()
      setNotice('Solicitação criada na fila Suporte N1. Agora oferte a um operador disponível.')
      navigate('/supervisao/filas')
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  async function offerNext(queueId:string){
    setBusy(true);setError('');setNotice('')
    try{
      const result = await api('/v1/dispatch/offer','POST',{queue_id:queueId,operation_id:'demo'})
      await refresh()
      if(result.result==='offered'){
        setOperatorId(result.offer.operator_id)
        navigate('/operador')
      }else if(result.result==='no_operator_available'){
        setNotice('Nenhum operador disponível ou com capacidade nesta fila.')
      }else{
        setNotice('Fila vazia: não há solicitação aguardando oferta.')
      }
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  async function changePresence(operator:string,presence:string){
    setBusy(true);setError('')
    try{
      await api('/v1/operators/'+operator+'/presence','PATCH',{presence})
      await refresh()
      setNotice('Presença demonstrativa atualizada.')
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  function openOperator(id:string){
    setOperatorId(id)
    navigate('/operador')
  }

  if(!connected)return <div className="login-wrap">
    <section className="login-panel">
      <div className="app-mark"><Headset size={26}/></div>
      <span className="kicker">HANDOFF HUB · SQLITE POC</span>
      <h1>Uma plataforma. Workspaces independentes.</h1>
      <p>Acesse a Mesa do Operador, a Supervisão ou o Laboratório. A navegação é separada, mas utiliza a mesma operação demonstrativa.</p>
      <label htmlFor="poc-key">Chave de acesso local</label>
      <input id="poc-key" type="password" autoComplete="off" value={key}
        onChange={e=>setKey(e.target.value)}
        onKeyDown={e=>{if(e.key==='Enter')void connect()}}
        placeholder="Chave exibida pelo start.cmd"/>
      <button className="primary full" disabled={!key||busy} onClick={()=>void connect()}>
        <Lock size={16}/> Entrar no Handoff Hub <ArrowRight size={16}/>
      </button>
      {error&&<p className="alert" role="alert">{error}</p>}
      <small>POC local · Sem Entra ID ou controle de acesso individual</small>
    </section>
  </div>

  if(operatorMode)return <div className="operator-portal">
    <header className="operator-portal__header">
      <Logo/>
      <div className="operator-portal__location"><Headset size={17}/> Portal do Operador
        <span>Workspace dedicado</span></div>
      <div className="operator-portal__actions">
        <span className="local-tag"><ShieldCheck size={15}/> SIMULAÇÃO LOCAL</span>
        <button className="outline" onClick={()=>navigate('/supervisao')}>
          <ArrowLeftRight size={16}/> Ir para Supervisão
        </button>
      </div>
    </header>
    <main className="operator-portal__main">
      <Routes>
        <Route path="/operador" element={<OperatorDesk
          operators={snapshot.operators}
          queues={snapshot.queues}
          api={api}
          preferredOperatorId={operatorId}
          onChanged={refresh}
          onGoQueues={()=>navigate('/supervisao/filas')}
        />}/>
        <Route path="*" element={<Navigate to="/operador" replace/>}/>
      </Routes>
    </main>
    <div className="portal-disclaimer">POC 0.4 · A seleção do operador ainda é simulada · Nenhuma mensagem é entregue ao Teams</div>
  </div>

  if(adminMode)return <div className="admin-portal">
    <aside className="sidebar sidebar--admin">
      <Logo/>
      <div className="sidebar-title">ADMINISTRAÇÃO</div>
      <ActiveLink to="/administracao" icon={<Settings2 size={18}/>} label="Visão administrativa"/>
      <div className="sidebar-bottom"><span className="online-dot"/> Ambiente local
        <small>Funções planejadas · Não operacionais</small></div>
    </aside>
    <main className="admin-portal__main">
      <header className="portal-topbar"><span>Administração / POC 0.4</span>
        <button className="outline" onClick={()=>navigate('/supervisao')}>
          <ArrowLeftRight size={15}/> Voltar à Supervisão
        </button></header>
      <Routes><Route path="/administracao" element={<AdminLanding/>}/>
        <Route path="*" element={<Navigate to="/administracao" replace/>}/></Routes>
    </main>
  </div>

  return <div className="layout layout--supervisor">
    <aside className="sidebar sidebar--supervisor">
      <Logo/>
      <span className="sidebar-title">CENTRAL DE SUPERVISÃO</span>
      <ActiveLink to="/supervisao" icon={<ChartNoAxesCombined size={18}/>} label="Visão geral"/>
      <ActiveLink to="/supervisao/conversas" icon={<MessageSquareText size={18}/>} label="Conversas" count={snapshot.handoffs.length}/>
      <ActiveLink to="/supervisao/filas" icon={<Layers size={18}/>} label="Filas" count={waiting+offered}/>
      <ActiveLink to="/supervisao/equipe" icon={<Users size={18}/>} label="Equipe"/>
      <div className="sidebar-separator"/>
      <span className="sidebar-title">AMBIENTE DE TESTES</span>
      <ActiveLink to="/laboratorio" icon={<FlaskConical size={18}/>} label="Laboratório"/>
      <div className="sidebar-separator"/>
      <span className="sidebar-title">OUTROS ESPAÇOS</span>
      <NavLink className="nav nav--external" to="/operador"><Headset size={18}/><span>Mesa do Operador</span><ArrowRight size={14}/></NavLink>
      <NavLink className="nav nav--external" to="/administracao"><Settings2 size={18}/><span>Administração</span><ArrowRight size={14}/></NavLink>
      <div className="sidebar-bottom"><span className="online-dot"/> API local · SQLite
        <small>POC 0.4 · Sem integração Teams</small></div>
    </aside>
    <main className="supervisor-main">
      <header className="portal-topbar">
        <span>Handoff Hub / Operação demonstrativa</span>
        <div className="portal-topbar__actions">
          <span className="local-tag"><ShieldCheck size={15}/> AMBIENTE LOCAL</span>
          <button className="icon-btn" aria-label="Atualizar dados" onClick={()=>void refresh()}>
            <RefreshCw size={17}/>
          </button>
        </div>
      </header>
      {error&&<div className="alert" role="alert">{error}
        <button onClick={()=>setError('')}>Fechar</button></div>}
      {notice&&<div className="notice" role="status"><CheckCircle2 size={16}/>{notice}
        <button aria-label="Dispensar aviso" onClick={()=>setNotice('')}>×</button></div>}
      <Routes>
        <Route path="/" element={<Navigate to="/supervisao" replace/>}/>
        <Route path="/supervisao" element={<SupervisorOverview snapshot={snapshot}/>}/>
        <Route path="/supervisao/conversas" element={<SupervisorConversations
          tickets={snapshot.handoffs} api={api}/>}/>
        <Route path="/supervisao/filas" element={<SupervisorQueues
          queues={snapshot.queues} operators={snapshot.operators}
          tickets={snapshot.handoffs} busy={busy}
          onOffer={offerNext} onOpenOperator={openOperator}/>}/>
        <Route path="/supervisao/equipe" element={<SupervisorTeam
          operators={snapshot.operators} busy={busy} onPresence={changePresence}/>}/>
        <Route path="/laboratorio" element={<DemoLab
          tickets={snapshot.handoffs} busy={busy} onCreate={createTicket}/>}/>
        <Route path="*" element={<Navigate to="/supervisao" replace/>}/>
      </Routes>
      <footer>Handoff Hub · POC SQLite 0.4 · Identidades demonstrativas · Dados locais</footer>
    </main>
  </div>
}
