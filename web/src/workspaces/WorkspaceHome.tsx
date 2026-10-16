import { ArrowRight, FlaskConical, Headset, Shield, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const spaces = [
  {name:'Mesa do Operador',path:'/operador',
    description:'Minhas ofertas, atendimentos, mensagens, transferências e encerramentos.',
    icon:<Headset size={24}/>,kind:'operator',status:'Operacional na POC'},
  {name:'Central de Supervisão',path:'/supervisao',
    description:'Visão geral, monitoramento das filas, equipe e histórico.',
    icon:<Users size={24}/>,kind:'supervisor',status:'Operacional na POC'},
  {name:'Administração',path:'/administracao',
    description:'Bots, operações, permissões e políticas do produto.',
    icon:<Shield size={24}/>,kind:'admin',status:'Estrutura planejada'},
  {name:'Laboratório',path:'/laboratorio',
    description:'Crie solicitações fictícias e valide o ciclo de atendimento.',
    icon:<FlaskConical size={24}/>,kind:'lab',status:'Somente testes'},
]

export default function WorkspaceHome(){
  const navigate=useNavigate()
  return <div className="workspace-home">
    <div className="workspace-home__intro">
      <span className="eyebrow">HANDOFF HUB · MULTICHANNEL PLATFORM</span>
      <h1>Qual espaço você deseja acessar?</h1>
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
  </div>
}
