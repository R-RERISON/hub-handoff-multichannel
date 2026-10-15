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
import WorkspaceHome from './workspaces/WorkspaceHome'
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
  const [username,setUsername] = useState('')
  const [password,setPassword] = useState('')
  const [token,setToken] = useState('')
  const [user,setUser] = useState<{username:string;role:'ADMIN'|'SUPERVISOR'|'OPERATOR'|'AUDITOR';operator_id:string|null}|null>(null)
  const [connected,setConnected] = useState(false)
  const [snapshot,setSnapshot] = useState<DashboardSnapshot>(EMPTY_SNAPSHOT)
  const [operatorId,setOperatorId] = useState('op-ana')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const homeMode = location.pathname==='/' || location.pathname==='/inicio'
  const operatorMode = location.pathname.startsWith('/operador')
  const adminMode = location.pathname.startsWith('/administracao')
  const offered = snapshot.handoffs.filter(t=>t.status==='OFFERED').length
  const waiting = snapshot.queues.reduce((sum,q)=>sum+q.waiting,0)

  const api:Api = useCallback(async (
    path:string,method='GET',body?:object,extra?:Record<string,string>
  )=>{
    const response = await fetch(API_URL+path, {
      method,
      headers: {'Authorization':'Bearer '+token,'Content-Type':'application/json',...(extra||{})},
      body: body ? JSON.stringify(body) : undefined,
    })
    if(!response.ok)throw new Error(String(response.status)+': '+(await response.text()).slice(0,240))
    return response.json()
  },[token])

  const refresh = useCallback(async ()=>{
    if(!connected)return
    try {
      if(user?.role==='OPERATOR'){
        const queues=await api('/v1/queues')
        setSnapshot(s=>({...s,queues}))
      }else{
        const data:DashboardSnapshot = await api('/v1/dashboard')
        setSnapshot(data)
      }
    }catch(e){setError((e as Error).message)}
  },[connected,api,user?.role])

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
    if(!connected||!token)return
    const ping=()=>{if(document.visibilityState==='visible')void api('/v1/auth/heartbeat','POST').catch(e=>setError((e as Error).message))}
    ping()
    const id=window.setInterval(ping,10000)
    document.addEventListener('visibilitychange',ping)
    return ()=>{window.clearInterval(id);document.removeEventListener('visibilitychange',ping)}
  },[connected,token,api])

  useEffect(()=>{
    setError('')
    setNotice('')
  },[location.pathname])

  async function connect(){
    setBusy(true);setError('')
    try{
      const response=await fetch(API_URL+'/v1/auth/login',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username:username.trim().toLowerCase(),password})
      })
      if(!response.ok)throw new Error('Usuário ou senha inválidos.')
      const result=await response.json()
      const accessToken:string=result.access_token
      const principal=result.user as NonNullable<typeof user>
      const headers={'Authorization':'Bearer '+accessToken}
      if(principal.role==='OPERATOR'){
        const r=await fetch(API_URL+'/v1/queues',{headers})
        if(!r.ok)throw new Error('Falha ao carregar filas')
        const queues=await r.json()
        const display=principal.username.split('.')[0]
        setSnapshot({...EMPTY_SNAPSHOT,queues,operators:[{
          id:principal.operator_id??'',name:display.charAt(0).toUpperCase()+display.slice(1),
          presence:'AVAILABLE',capacity:1,active:0,offered:0
        }]})
        setOperatorId(principal.operator_id??'')
      }else{
        const r=await fetch(API_URL+'/v1/dashboard',{headers})
        if(!r.ok)throw new Error('Falha ao carregar a operação')
        setSnapshot(await r.json())
      }
      setToken(accessToken);setUser(principal);setConnected(true);setPassword('')
      const path=principal.role==='OPERATOR'?'/operador'
        :principal.role==='AUDITOR'?'/supervisao/conversas'
        :principal.role==='SUPERVISOR'?'/supervisao':'/inicio'
      navigate(path,{replace:true})
    }catch(e){setError((e as Error).message)}
    finally{setBusy(false)}
  }

  async function logout(){
    try{await api('/v1/auth/logout','POST')}catch{ /* token expires if offline */ }
    setToken('');setUser(null);setConnected(false);setSnapshot(EMPTY_SNAPSHOT)
    setNotice('');setError('');navigate('/',{replace:true})
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
      setNotice('Solicitação criada. A distribuição ocorrerá automaticamente quando houver operador conectado e disponível.')
      navigate('/supervisao/filas')
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

  if(!connected)return <div className="login-wrap">
    <section className="login-panel">
      <div className="app-mark"><Headset size={26}/></div>
      <span className="kicker">HANDOFF HUB · SQLITE POC</span>
      <h1>Bem-vindo ao Handoff Hub.</h1>
      <p>Acesse com seu perfil de operador, supervisor, auditor ou administrador. A API valida suas permissões.</p>
      <label htmlFor="username">Usuário</label>
      <input id="username" autoComplete="username" value={username}
        onChange={e=>setUsername(e.target.value)} placeholder="ex.: ana.demo"/>
      <label htmlFor="password">Senha</label>
      <input id="password" type="password" autoComplete="current-password" value={password}
        onChange={e=>setPassword(e.target.value)}
        onKeyDown={e=>{if(e.key==='Enter')void connect()}}/>
      <button className="primary full" disabled={!username.trim()||!password||busy} onClick={()=>void connect()}>
        <Lock size={16}/> Entrar no meu workspace <ArrowRight size={16}/>
      </button>
      {error&&<p className="alert" role="alert">{error}</p>}
      <small>Credenciais geradas em data/demo-credentials.txt · POC local sem SSO</small>
    </section>
  </div>

  const permitted=!!user && ((user.role==='ADMIN' && !operatorMode) ||
    (user.role==='OPERATOR' && operatorMode) ||
    (user.role==='SUPERVISOR' && (
      location.pathname.startsWith('/supervisao') || location.pathname==='/laboratorio')) ||
    (user.role==='AUDITOR' && (
      location.pathname==='/supervisao' || location.pathname==='/supervisao/conversas')))
  if(!permitted)return <div className="login-wrap"><section className="login-panel">
    <h1>Acesso não permitido</h1><p>Este espaço não pertence ao seu perfil.</p>
    <button className="primary full" onClick={()=>navigate(user?.role==='OPERATOR'?'/operador':
      user?.role==='AUDITOR'?'/supervisao/conversas':'/supervisao')}>Ir para meu workspace</button>
    <button className="outline full" onClick={()=>void logout()}>Sair</button>
  </section></div>

  if(homeMode)return <WorkspaceHome/>

  if(operatorMode)return <div className="operator-portal">
    <header className="operator-portal__header">
      <Logo/>
      <div className="operator-portal__location"><Headset size={17}/> Portal do Operador
        <span>Workspace dedicado</span></div>
      <div className="operator-portal__actions">
        <span className="local-tag"><ShieldCheck size={15}/> SIMULAÇÃO LOCAL</span>
        <button className="outline" onClick={()=>void logout()}>
          <ArrowLeftRight size={16}/> Sair
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
          lockedIdentity={user?.role==='OPERATOR'}
          onChanged={refresh}
          onGoQueues={()=>navigate('/supervisao/filas')}
        />}/>
        <Route path="*" element={<Navigate to="/operador" replace/>}/>
      </Routes>
    </main>
    <div className="portal-disclaimer">POC 0.5 · Perfil autenticado · Sem entrega externa ao Teams</div>
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
        <button className="outline" onClick={()=>navigate('/inicio')}>
          <ArrowLeftRight size={15}/> Trocar espaço
        </button><button className="outline" onClick={()=>void logout()}>Sair</button></header>
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
      {user?.role!=='AUDITOR'&&<>
        <ActiveLink to="/supervisao/filas" icon={<Layers size={18}/>} label="Filas" count={waiting+offered}/>
        <ActiveLink to="/supervisao/equipe" icon={<Users size={18}/>} label="Equipe"/>
      </>}
      <div className="sidebar-separator"/>
      <span className="sidebar-title">AMBIENTE DE TESTES</span>
      {user?.role!=='AUDITOR'&&<ActiveLink to="/laboratorio" icon={<FlaskConical size={18}/>} label="Laboratório"/>}
      <div className="sidebar-separator"/>
      <span className="sidebar-title">OUTROS ESPAÇOS</span>
      {user?.role==='ADMIN'&&<NavLink className="nav nav--external" to="/inicio"><ArrowLeftRight size={18}/><span>Escolher espaço</span><ArrowRight size={14}/></NavLink>}
      <div className="sidebar-bottom"><span className="online-dot"/> API local · SQLite
        <small>POC 0.4 · Sem integração Teams</small></div>
    </aside>
    <main className="supervisor-main">
      <header className="portal-topbar">
        <span>Handoff Hub / Operação demonstrativa</span>
        <div className="portal-topbar__actions">
          <span className="local-tag"><ShieldCheck size={15}/> AMBIENTE LOCAL</span>
          <button className="outline" onClick={()=>void logout()}>Sair ({user?.username})</button>
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
          tickets={snapshot.handoffs} api={api}/>}/>
        <Route path="/supervisao/equipe" element={<SupervisorTeam
          operators={snapshot.operators} busy={busy} onPresence={changePresence}/>}/>
        <Route path="/laboratorio" element={<DemoLab
          tickets={snapshot.handoffs} busy={busy} onCreate={createTicket}/>}/>
        <Route path="*" element={<Navigate to="/supervisao" replace/>}/>
      </Routes>
      <footer>Handoff Hub · POC SQLite 0.5 · Controle de acesso por perfil · Uso local</footer>
    </main>
  </div>
}
