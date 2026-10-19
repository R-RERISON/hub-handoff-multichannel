import { ArrowRight, FlaskConical, Plus, ShieldAlert } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { Ticket } from './types'

type Props = {tickets:Ticket[];busy:boolean;onCreate:()=>Promise<void>}

export default function DemoLab({tickets,busy,onCreate}:Props) {
  const navigate=useNavigate()
  return <div className="section-stack">
    <section className="intro-banner intro-banner--lab"><div>
      <span className="eyebrow">AMBIENTE DE HOMOLOGAÇÃO</span>
      <h2>Laboratório de simulação</h2>
      <p>Gere solicitações fictícias para validar a distribuição, os atendimentos, as transferências e a auditoria, sem conectar bots externos.</p>
    </div><div className="banner-icon"><FlaskConical size={28}/></div></section>
    <section className="panel lab-onboarding">
      <div className="lab-stage"><span>01</span><b>Crie uma solicitação</b><p>Ela entrará na fila Suporte N1.</p></div>
      <div className="lab-stage"><span>02</span><b>Distribuição automática</b><p>O sistema identifica operadores online e disponíveis e envia a oferta.</p></div>
      <div className="lab-stage"><span>03</span><b>Atenda na Mesa</b><p>Aceite, converse, transfira ou encerre.</p></div>
      <div className="lab-stage"><span>04</span><b>Audite em Supervisão</b><p>Confira histórico e estado da sessão.</p></div>
    </section>
    <section className="panel lab-cta">
      <div><h3>Nova solicitação de teste</h3><p>Somente dados sintéticos. O banco SQLite local será atualizado.</p></div>
      <button className="primary" disabled={busy} onClick={()=>void onCreate()}><Plus size={16}/> Criar solicitação simulada</button>
    </section>
    <section className="panel lab-cta"><div>
      <h3>Continuar a homologação</h3><p>{tickets.filter(t=>t.status==='QUEUED').length} solicitação(ões) aguardando distribuição.</p>
    </div><button className="outline" onClick={()=>navigate('/supervisao/filas')}>Abrir filas <ArrowRight size={16}/></button></section>
    <p className="operational-note"><ShieldAlert size={15}/> Contas de laboratório com RBAC no backend. Sem identidade corporativa/SSO ou entrega real no Microsoft Teams.</p>
  </div>
}
