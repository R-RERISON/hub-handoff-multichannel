import { Users } from 'lucide-react'
import type { Operator } from './types'

type Props = {
  operators: Operator[]
  busy: boolean
  onPresence: (operatorId:string,presence:string)=>Promise<void>
  onCapacity: (operatorId:string,capacity:number)=>Promise<void>
}

export default function SupervisorTeam({operators,busy,onPresence,onCapacity}:Props) {
  return <div className="section-stack">
    <section className="intro-banner"><div>
      <span className="eyebrow">SUPERVISÃO / EQUIPE</span>
      <h2>Equipe de atendimento</h2>
      <p>Capacidade, presença e ocupação por operador.</p>
    </div><div className="banner-icon"><Users size={28}/></div></section>
    <section className="panel team-table">
      <div className="panel-header"><div><h3>Operadores da operação</h3>
        <p>Alterações de presença são demonstrativas e não representam status real do Teams ou Finesse.</p></div></div>
      <div className="team-table__head"><span>Operador</span><span>Ocupação</span><span>Ofertas</span><span>Presença</span></div>
      {operators.map(o=><div className="team-row" key={o.id}>
        <div className="team-identity"><div className="avatar">{o.name.slice(0,2).toUpperCase()}</div><div><b>{o.name}</b><small>{o.id}</small></div></div>
        <div><label className="capacity-label" htmlFor={'capacity-'+o.id}>Capacidade</label>
          <select id={'capacity-'+o.id} aria-label={'Capacidade de '+o.name}
            value={o.capacity} disabled={busy}
            onChange={e=>void onCapacity(o.id,Number(e.target.value))}>
            {[1,2,3,4,5].map(n=><option key={n} value={n}>{n} atendimento(s)</option>)}
          </select><small>{o.active} ativo(s)</small>
        </div>
        <div><b>{o.offered??0}</b><small>Reservas pendentes</small></div>
        <select aria-label={'Presença de '+o.name} value={o.presence} disabled={busy} onChange={e=>void onPresence(o.id,e.target.value)}>
          <option value="AVAILABLE">Disponível</option>
          <option value="AWAY">Em pausa</option>
          <option value="OFFLINE">Offline</option>
        </select>
      </div>)}
      {operators.length===0&&<div className="empty-state">Nenhum operador disponível nesta operação.</div>}
    </section>
  </div>
}
