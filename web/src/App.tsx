import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  ArrowLeftRight, ArrowRight, ChartNoAxesCombined,
  CheckCircle2, FlaskConical, Headset, Layers, Lock,
  MessageSquareText, RefreshCw, Settings2, ShieldCheck, Users
} from 'lucide-react'
import OperatorDesk from './OperatorDesk'
import AdminLanding from './workspaces/AdminLanding'
import DemoLab from './workspaces/DemoLab'
import { userFacingError } from './design-system/presentation'
import SupervisorConversations from './workspaces/SupervisorConversations'
import SupervisorOverview from './workspaces/SupervisorOverview'
import SupervisorQueues from './workspaces/SupervisorQueues'
import SupervisorTeam from './workspaces/SupervisorTeam'
import WorkspaceHome from './workspaces/WorkspaceHome'
import { ApiError, type Api, type DashboardSnapshot } from './workspaces/types'

const API_URL = 'http://127.0.0.1:8000'
const EMPTY_SNAPSHOT: DashboardSnapshot = {
  handoffs: [], queues: [], operators: [], outbox: { total: 0, pending: 0 },
}

function Logo() {
  return <div className="brand">
    <div className="app-mark"><Headset size={20}/></div>
    <div><b>Handoff Hub</b><small>PLATAFORMA MULTICANAL</small></div>
  </div>
}

function ActiveLink({to,icon,label,count,countMeaning}:{
  to:string;icon:ReactNode;label:string;count?:number;countMeaning?:string
}) {
  return <NavLink to={to} end={to==='/supervisao'} aria-label={label} title={label}
    className={({isActive})=>'nav '+(isActive?'active':'')}>
    {icon}<span>{label}</span>
    {count!==undefined&&<em title={countMeaning} aria-label={countMeaning??String(count)}>{count}</em>}
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
  const [snapshotUnavailable,setSnapshotUnavailable] = useState('')
  const snapshotRequestRef = useRef(0)
  const [operatorId,setOperatorId] = useState('op-ana')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const homeMode = location.pathname==='/' || location.pathname==='/inicio'
  const operatorMode = location.pathname.startsWith('/operador')
  const adminMode = location.pathname.startsWith('/administracao')
  const offered = snapshot.handoffs.filter(t=>t.status==='OFFERED').length
  const waiting = snapshot.queues.reduce((sum,q)=>sum+q.waiting,0)

  useEffect(()=>{
    document.querySelector<HTMLElement>('[data-page-focus]')?.focus()
  },[connected,location.pathname])

  const api:Api = useCallback(async (
    path:string,method='GET',body?:object,extra?:Record<string,string>
  )=>{
    const response = await fetch(API_URL+path, {
      method,
      headers: {'Authorization':'Bearer '+token,'Content-Type':'application/json',...(extra||{})},
      body: body ? JSON.stringify(body) : undefined,
    })
    if(!response.ok)throw new ApiError(
      response.status,String(response.status)+': '+(await response.text()).slice(0,240)
    )
    return response.json()
  },[token])

  const refresh = useCallback(async ()=>{
    if(!connected)return
    const requestId=++snapshotRequestRef.current
    try {
      if(user?.role==='OPERATOR'){
        const queues=await api('/v1/queues')
        if(requestId!==snapshotRequestRef.current)return
        setSnapshot(s=>({...s,queues}))
      }else{
        const data:DashboardSnapshot = await api('/v1/dashboard')
        if(requestId!==snapshotRequestRef.current)return
        setSnapshot(data)
      }
      setSnapshotUnavailable('')
      setError('')
    }catch(e){
      if(requestId!==snapshotRequestRef.current)return
      setSnapshot(EMPTY_SNAPSHOT)
      if(e instanceof ApiError&&e.status===401){
        snapshotRequestRef.current+=1
        setToken('');setUser(null);setConnected(false)
        setSnapshotUnavailable('')
        setError('Sessão expirada ou revogada. Faça login novamente.')
        return
      }
      setSnapshotUnavailable(e instanceof ApiError&&e.status===403
        ? 'A autorização foi revogada ou não cobre este escopo. Os dados protegidos foram removidos.'
        : 'Não foi possível atualizar a operação. Os dados protegidos foram removidos.')
      setError('')
    }
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
    const ping=()=>{void api('/v1/auth/heartbeat','POST').catch(e=>{
      if(e instanceof ApiError&&(e.status===401||e.status===403)){
        void refresh()
        return
      }
      setError(userFacingError(e,'Não foi possível confirmar a sessão. Atualize os dados antes de continuar.'))
    })}
    ping()
    const id=window.setInterval(ping,10000)
    document.addEventListener('visibilitychange',ping)
    return ()=>{window.clearInterval(id);document.removeEventListener('visibilitychange',ping)}
  },[connected,token,api,refresh])

  useEffect(()=>{
    setError('')
    setNotice('')
  },[location.pathname])

  async function connect(){
    snapshotRequestRef.current+=1
    setBusy(true);setError('')
    setSnapshotUnavailable('')
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
      setSnapshotUnavailable('')
      const path=principal.role==='OPERATOR'?'/operador'
        :principal.role==='AUDITOR'?'/supervisao/conversas'
        :principal.role==='SUPERVISOR'?'/supervisao':'/inicio'
      navigate(path,{replace:true})
    }catch(e){setError(userFacingError(e,'Usuário ou senha inválidos. Confira os dados e a disponibilidade do serviço local.'))}
    finally{setBusy(false)}
  }

  async function logout(){
    const logoutRequest=api('/v1/auth/logout','POST')
    snapshotRequestRef.current+=1
    setToken('');setUser(null);setConnected(false);setSnapshot(EMPTY_SNAPSHOT)
    setSnapshotUnavailable('')
    setNotice('');setError('');navigate('/',{replace:true})
    try{await logoutRequest}catch{ /* Local state is cleared; the server session expires if offline. */ }
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
    }catch(e){setError(userFacingError(e,'Não foi possível criar a solicitação sintética. Atualize os dados e tente novamente.'))}
    finally{setBusy(false)}
  }

  async function changeCapacity(operator:string,capacity:number){
    setBusy(true);setError('')
    try{
      await api('/v1/operators/'+operator+'/capacity','PATCH',{capacity})
      await refresh()
    }
    finally{setBusy(false)}
  }

  async function changePresence(operator:string,presence:string){
    setBusy(true);setError('')
    try{
      await api('/v1/operators/'+operator+'/presence','PATCH',{presence})
      await refresh()
    }
    finally{setBusy(false)}
  }

  if(!connected)return <main className="login-wrap">
    <section className="login-panel" aria-labelledby="login-heading">
      <div className="app-mark"><Headset size={26}/></div>
      <span className="kicker">HANDOFF HUB · SQLITE POC</span>
      <h1 id="login-heading" tabIndex={-1} data-page-focus>Bem-vindo ao Handoff Hub.</h1>
      <p>Acesse com seu perfil de operador, supervisor, auditor ou administrador. A API valida suas permissões.</p>
      <form aria-busy={busy} onSubmit={event=>{event.preventDefault();void connect()}}>
        <label htmlFor="username">Usuário</label>
        <input id="username" required autoComplete="username" value={username}
          aria-invalid={!!error} onChange={e=>setUsername(e.target.value)} placeholder="ex.: ana.demo"/>
        <label htmlFor="password">Senha</label>
        <input id="password" type="password" required autoComplete="current-password" value={password}
          aria-invalid={!!error} onChange={e=>setPassword(e.target.value)}/>
        <button className="primary full" type="submit" disabled={!username.trim()||!password||busy}>
          <Lock size={16}/> {busy?'Entrando…':'Entrar no meu workspace'} <ArrowRight size={16}/>
        </button>
        {error&&<p className="alert" role="alert" aria-live="assertive">{error}</p>}
      </form>
      <small>Use as credenciais do ambiente iniciado pelo launcher.
        No laboratório, elas ficam exclusivamente no diretório TEMP informado no terminal.
        POC local sem SSO.</small>
    </section>
  </main>

  const permitted=!!user && ((user.role==='ADMIN' && !operatorMode) ||
    (user.role==='OPERATOR' && operatorMode) ||
    (user.role==='SUPERVISOR' && (
      location.pathname.startsWith('/supervisao') || location.pathname==='/laboratorio')) ||
    (user.role==='AUDITOR' && (
      location.pathname==='/supervisao' || location.pathname==='/supervisao/conversas')))
  if(!permitted)return <main className="login-wrap"><section className="login-panel"
    aria-labelledby="access-denied-heading">
    <h1 id="access-denied-heading" tabIndex={-1} data-page-focus>Acesso não permitido</h1>
    <p>Este espaço não pertence ao seu perfil.</p>
    <button className="primary full" onClick={()=>navigate(user?.role==='OPERATOR'?'/operador':
      user?.role==='AUDITOR'?'/supervisao/conversas':'/supervisao')}>Ir para meu workspace</button>
    <button className="outline full" onClick={()=>void logout()}>Sair</button>
  </section></main>

  if(homeMode)return <WorkspaceHome onLogout={()=>void logout()}/>

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
      <header className="portal-topbar"><span>Administração / POC 0.5</span>
        <button className="outline" onClick={()=>navigate('/inicio')}>
          <ArrowLeftRight size={15}/> Trocar espaço
        </button><button className="outline" onClick={()=>void logout()}>Sair</button></header>
      <Routes><Route path="/administracao" element={<AdminLanding api={api} onChanged={refresh}/>}/>
        <Route path="*" element={<Navigate to="/administracao" replace/>}/></Routes>
    </main>
  </div>

  return <div className="layout layout--supervisor">
    <aside className="sidebar sidebar--supervisor">
      <Logo/>
      <span className="sidebar-title">CENTRAL DE SUPERVISÃO</span>
      <ActiveLink to="/supervisao" icon={<ChartNoAxesCombined size={18}/>} label="Visão geral"/>
      <ActiveLink to="/supervisao/conversas" icon={<MessageSquareText size={18}/>} label="Conversas" count={snapshot.handoffs.length}
        countMeaning="Quantidade de atendimentos correntes; não inclui o histórico verificado"/>
      {user?.role!=='AUDITOR'&&<>
        <ActiveLink to="/supervisao/filas" icon={<Layers size={18}/>} label="Filas" count={waiting+offered}/>
        <ActiveLink to="/supervisao/equipe" icon={<Users size={18}/>} label="Equipe"/>
      </>}
      {user?.role!=='AUDITOR'&&<>
        <div className="sidebar-separator"/>
        <span className="sidebar-title">AMBIENTE DE TESTES</span>
        <ActiveLink to="/laboratorio" icon={<FlaskConical size={18}/>} label="Laboratório"/>
      </>}
      {user?.role==='ADMIN'&&<>
        <div className="sidebar-separator"/>
        <span className="sidebar-title">OUTROS ESPAÇOS</span>
        <NavLink className="nav nav--external" to="/inicio" aria-label="Escolher espaço"
          title="Escolher espaço"><ArrowLeftRight size={18}/><span>Escolher espaço</span><ArrowRight size={14}/></NavLink>
      </>}
      <div className="sidebar-bottom"><span className="online-dot"/> API local · SQLite
        <small>POC 0.5 · Sem integração Teams</small></div>
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
      {snapshotUnavailable
        ? <section className="panel workspace-data-state" role="alert">
            <h2>Dados da operação indisponíveis</h2>
            <p>{snapshotUnavailable}</p>
            <button className="outline" type="button" onClick={()=>void refresh()}>
              Revalidar acesso
            </button>
          </section>
        : <Routes>
            <Route path="/" element={<Navigate to="/supervisao" replace/>}/>
            <Route path="/supervisao" element={<SupervisorOverview snapshot={snapshot}/>}/>
            <Route path="/supervisao/conversas" element={<SupervisorConversations
              tickets={snapshot.handoffs} api={api}
              showVerified={user?.role==='SUPERVISOR'||user?.role==='AUDITOR'}/>}/>
            <Route path="/supervisao/filas" element={<SupervisorQueues
              queues={snapshot.queues} operators={snapshot.operators}
              tickets={snapshot.handoffs} api={api} onChanged={refresh}/>}/>
            <Route path="/supervisao/equipe" element={<SupervisorTeam
              operators={snapshot.operators} busy={busy} onPresence={changePresence}
              onCapacity={changeCapacity} onRefresh={refresh}/>}/>
            <Route path="/laboratorio" element={<DemoLab
              tickets={snapshot.handoffs} busy={busy} onCreate={createTicket}/>}/>
            <Route path="*" element={<Navigate to="/supervisao" replace/>}/>
          </Routes>}
      <footer>Handoff Hub · POC SQLite 0.5 · Controle de acesso por perfil · Uso local</footer>
    </main>
  </div>
}
