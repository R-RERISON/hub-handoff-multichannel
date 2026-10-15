import { Bot, KeyRound, Settings2, Shield, SlidersHorizontal } from 'lucide-react'

export default function AdminLanding(){
  const areas=[
    {title:'Bots e integrações',description:'Cadastro de bots, capacidades por canal, credenciais e webhooks.',icon:<Bot size={21}/>},
    {title:'Operações e filas',description:'Definição de operações, skills, roteamento e turnos.',icon:<Settings2 size={21}/>},
    {title:'Perfis e permissões',description:'Entra ID, papéis por operação e segregação de acesso.',icon:<KeyRound size={21}/>},
    {title:'Políticas operacionais',description:'SLA, limites de capacidade, auditoria e retenção de dados.',icon:<SlidersHorizontal size={21}/>}
  ]
  return <div className="section-stack">
    <section className="intro-banner"><div><span className="eyebrow">ADMINISTRAÇÃO / PLANEJAMENTO</span>
      <h2>Administração do Handoff Hub</h2>
      <p>Área independente reservada ao futuro controle da plataforma. Ainda não existem formulários de produção nesta POC.</p>
    </div><div className="banner-icon"><Shield size={28}/></div></section>
    <div className="admin-cards">
      {areas.map(a=><section className="panel admin-card" key={a.title}>
        <span className="admin-card__icon">{a.icon}</span><h3>{a.title}</h3>
        <p>{a.description}</p><small>Planejado · não implementado</small>
      </section>)}
    </div>
    <p className="operational-note">A navegação está separada desde já para impedir que ações administrativas sejam misturadas com o workspace do operador. O acesso por papéis ainda não está protegido nesta POC.</p>
  </div>
}
