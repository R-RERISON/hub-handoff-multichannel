import { useRef, useState } from 'react'
import { Users } from 'lucide-react'
import { ConfirmDialog } from '../design-system/ConfirmDialog'
import { presenceLabel, userFacingError } from '../design-system/presentation'
import { ApiError, type Operator } from './types'

type PendingChange = {
  operatorId:string
  operatorName:string
  field:'presence'|'capacity'
  current:string
  next:string
}
type Props = {
  operators: Operator[]
  busy: boolean
  onPresence: (operatorId:string,presence:string)=>Promise<void>
  onCapacity: (operatorId:string,capacity:number)=>Promise<void>
  onRefresh: ()=>Promise<void>
}

export default function SupervisorTeam({operators,busy,onPresence,onCapacity,onRefresh}:Props) {
  const [pendingChange,setPendingChange] = useState<PendingChange|null>(null)
  const [saving,setSaving] = useState(false)
  const [denied,setDenied] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const requestRef = useRef(false)

  function requestChange(operator:Operator,field:'presence'|'capacity',next:string) {
    if(busy||saving||denied)return
    const current=field==='presence'?operator.presence:String(operator.capacity)
    if(current===next)return
    setError('')
    setNotice('')
    setPendingChange({
      operatorId:operator.id,
      operatorName:operator.name,
      field,
      current,
      next,
    })
  }

  async function commitChange() {
    if(!pendingChange||requestRef.current||busy)return
    requestRef.current=true
    const change=pendingChange
    setSaving(true)
    setError('')
    setNotice('')
    try{
      if(change.field==='presence')await onPresence(change.operatorId,change.next)
      else await onCapacity(change.operatorId,Number(change.next))
      setPendingChange(null)
      setNotice(change.field==='presence'
        ? `Presença de ${change.operatorName} atualizada para ${presenceLabel(change.next)}.`
        : `Capacidade de ${change.operatorName} atualizada para ${change.next}.`)
    }catch(e){
      setPendingChange(null)
      if(e instanceof ApiError&&[401,403,404].includes(e.status))setDenied(true)
      setError('Resultado não confirmado. '+userFacingError(e,'Atualize o inventário antes de tentar novamente.'))
    }finally{
      requestRef.current=false
      setSaving(false)
    }
  }

  async function revalidate() {
    await onRefresh()
    setDenied(false)
    setError('')
  }

  const currentLabel=pendingChange
    ? pendingChange.field==='presence'
      ? presenceLabel(pendingChange.current)
      : pendingChange.current
    : ''
  const nextLabel=pendingChange
    ? pendingChange.field==='presence'
      ? presenceLabel(pendingChange.next)
      : pendingChange.next
    : ''
  const confirmationDescription=pendingChange
    ? pendingChange.field==='presence'
      ? `A presença de ${pendingChange.operatorName} mudará de ${currentLabel} para ${nextLabel}. A alteração controla a elegibilidade para novas ofertas.`
      : `A capacidade de ${pendingChange.operatorName} mudará de ${currentLabel} para ${nextLabel} atendimentos simultâneos. A alteração controla futuras ofertas.`
    : ''

  return <div className="section-stack">
    <section className="intro-banner"><div>
      <span className="eyebrow">SUPERVISÃO / EQUIPE</span>
      <h2 tabIndex={-1} data-page-focus>Equipe de atendimento</h2>
      <p>Capacidade, presença e ocupação por operador.</p>
    </div><div className="banner-icon"><Users size={28}/></div></section>
    {error&&<div className="alert" role="alert">{error}</div>}
    {notice&&<div className="notice" role="status" aria-live="polite">{notice}</div>}
    {denied
      ? <section className="panel team-data-state" role="alert">
          <h3>Acesso à equipe não autorizado</h3>
          <p>Os dados de operadores foram removidos desta tela.</p>
          <button className="outline" type="button" onClick={()=>void revalidate()}>Revalidar acesso</button>
        </section>
      : <section className="panel team-table" aria-labelledby="team-table-heading">
        <div className="panel-header"><div><h3 id="team-table-heading">Operadores da operação</h3>
          <p>Alterações de presença são demonstrativas e não representam status real do Teams ou Finesse.</p></div></div>
        <p id="team-table-scroll-hint" className="admin-inventory__scroll-hint">
          Em telas estreitas, deslize a tabela para os lados. No teclado, foque a região e use as setas.
        </p>
        <div className="team-table__scroll" role="region" aria-label="Tabela de capacidade e presença da equipe"
          aria-describedby="team-table-scroll-hint"
          tabIndex={0}>
          <table>
            <caption>Equipe de atendimento ({operators.length} operadores)</caption>
            <thead><tr>
              <th scope="col">Operador</th>
              <th scope="col">Atendimentos ativos</th>
              <th scope="col">Ofertas pendentes</th>
              <th scope="col">Capacidade</th>
              <th scope="col">Presença</th>
            </tr></thead>
            <tbody>{operators.map(operator=><tr className="team-row" key={operator.id}>
              <th scope="row"><div className="team-identity">
                <div className="avatar" aria-hidden="true">{operator.name.slice(0,2).toUpperCase()}</div>
                <div><b>{operator.name}</b><small>{operator.id}</small></div>
              </div></th>
              <td>{operator.active}</td>
              <td>{operator.offered??0}</td>
              <td>
                <label className="sr-only" htmlFor={'capacity-'+operator.id}>Capacidade de {operator.name}</label>
                <select id={'capacity-'+operator.id} aria-label={'Capacidade de '+operator.name}
                  value={operator.capacity} disabled={busy||saving}
                  onChange={event=>requestChange(operator,'capacity',event.target.value)}>
                  {[1,2,3,4,5].map(number=>
                    <option key={number} value={number}>{number} atendimento(s)</option>)}
                </select>
              </td>
              <td>
                <label className="sr-only" htmlFor={'presence-'+operator.id}>Presença de {operator.name}</label>
                <select id={'presence-'+operator.id} aria-label={'Presença de '+operator.name}
                  value={operator.presence} disabled={busy||saving}
                  onChange={event=>requestChange(operator,'presence',event.target.value)}>
                  <option value="AVAILABLE">Disponível</option>
                  <option value="AWAY">Em pausa</option>
                  <option value="OFFLINE">Indisponível</option>
                </select>
              </td>
            </tr>)}</tbody>
          </table>
        </div>
        {operators.length===0&&<p className="empty-state" role="status">
          Nenhum operador disponível nesta operação.
        </p>}
      </section>}
    <ConfirmDialog open={!!pendingChange}
      title={pendingChange
        ? `${pendingChange.field==='presence'?'Alterar presença':'Alterar capacidade'} de ${pendingChange.operatorName}?`
        : 'Confirmar alteração da equipe'}
      description={confirmationDescription}
      confirmLabel="Confirmar alteração"
      busy={busy||saving}
      onCancel={()=>setPendingChange(null)}
      onConfirm={()=>void commitChange()}/>
  </div>
}
