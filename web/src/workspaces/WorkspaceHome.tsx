import { ArrowRight, FlaskConical, Headset, Shield, Users } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const spaces = [
  {name:'Mesa do Operador',path:'/operador',
    description:'Minhas ofertas, atendimentos, mensagens, transferências e encerramentos.',
    icon:<Headset size={24}/>,kind:'operator',status:'Operacional na POC'},
  {name:'Central de Supervisão',path:'/supervisao',
    description:'Visão geral demonstrativa de filas, equipe e histórico autorizado.',
    icon:<Users size={24}/>,kind:'supervisor',status:'Operacional na POC'},
  {name:'Administração',path:'/administracao',
    description:'Inventário da operação e ciclo de vida de filas disponíveis na POC.',
    icon:<Shield size={24}/>,kind:'admin',status:'Operacional na POC'},
  {name:'Laboratório',path:'/laboratorio',
    description:'Crie solicitações fictícias e valide o ciclo de atendimento.',
    icon:<FlaskConical size={24}/>,kind:'lab',status:'Somente testes'},
]

export default function WorkspaceHome({onLogout}:{onLogout:()=>void}){
  const navigate=useNavigate()
  const headingRef=useRef<HTMLHeadingElement|null>(null)
  useEffect(()=>headingRef.current?.focus(),[])
  return <main className="workspace-home" aria-labelledby="workspace-home-heading">
    <div className="workspace-home__actions">
      <button type="button" className="outline" onClick={onLogout}>Sair</button>
    </div>
    <div className="workspace-home__intro">
      <span className="eyebrow">HANDOFF HUB · PLATAFORMA MULTICANAL</span>
      <h1 id="workspace-home-heading" ref={headingRef} tabIndex={-1}>Qual espaço você deseja acessar?</h1>
      <p>O atendimento humano e a gestão operacional compartilham o mesmo núcleo, mas possuem interfaces e responsabilidades independentes.</p>
      <span className="workspace-home__warning">POC SQLite local · Seleção demonstrativa sem autenticação corporativa</span>
    </div>
    <div className="workspace-home__cards">
      {spaces.filter(space=>space.kind!=='operator').map(space=><button className={'workspace-home__card workspace-home__card--'+space.kind}
        key={space.path} onClick={()=>navigate(space.path)}>
        <span className="workspace-home__icon">{space.icon}</span>
        <span className="workspace-home__status">{space.status}</span>
        <strong>{space.name}</strong>
        <span className="workspace-home__description">{space.description}</span>
        <span className="workspace-home__open">Acessar espaço <ArrowRight size={16}/></span>
      </button>)}
    </div>
  </main>
}
