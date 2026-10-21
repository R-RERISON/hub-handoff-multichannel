import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, ShieldCheck, UsersRound } from 'lucide-react'
import type { Api } from './types'
import { EmptyState } from '../design-system/EmptyState'

type Membership = { queue_id:string; queue_name:string }
type OperatorRecord = {
  id:string; name:string; presence:string; capacity:number;
  active:number; offered:number; memberships:Membership[]
}
type AccountRecord = {
  id:string; username:string; role:string; is_active:boolean; operator_id:string|null
}
type PeopleInventory = {
  operation:{id:string;name:string}
  operators:OperatorRecord[]
  accounts:AccountRecord[]
  capabilities:{
    read_only:true; membership_write_available:false; grant_write_available:false;
    identity_provider:'LOCAL_POC'
  }
}

export default function AdminPeople({api}:{api:Api}){
  const [people,setPeople]=useState<PeopleInventory|null>(null)
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [filter,setFilter]=useState('')
  const refresh=useCallback(async()=>{
    setLoading(true);setError('');setPeople(null)
    try{
      const result:PeopleInventory=await api('/v1/admin/people')
      if(result.capabilities.read_only!==true||
         result.capabilities.membership_write_available!==false||
         result.capabilities.grant_write_available!==false)
        throw new Error('Contrato administrativo inesperado')
      setPeople(result)
    }catch{
      setError('Não foi possível consultar pessoas autorizadas. Nenhum resultado anterior foi mantido.')
    }finally{setLoading(false)}
  },[api])
  useEffect(()=>{void refresh()},[refresh])
  const search=filter.trim().toLocaleLowerCase('pt-BR')
  const operators=people?.operators.filter(operator=>
    (operator.name+' '+operator.id+' '+operator.memberships.map(m=>m.queue_name).join(' '))
      .toLocaleLowerCase('pt-BR').includes(search))??[]

  return <section className="panel admin-inventory__table" aria-labelledby="admin-people-heading">
    <header>
      <div>
        <span className="eyebrow">SPEC-007 / B1.0 · GOVERNANÇA DE PESSOAS</span>
        <h3 id="admin-people-heading"><UsersRound size={19}/> Pessoas e vínculos operacionais</h3>
        <p>Identidades autenticadas, perfis de operador e memberships são entidades independentes.
          Vínculo de despacho não concede acesso à fila.</p>
      </div>
      <span className="admin-inventory__tag"><ShieldCheck size={15}/> Consulta restrita a ADMIN</span>
    </header>
    <div className="admin-inventory__status">
      <span>Inventário somente leitura · sem concessões implícitas</span>
      <button type="button" className="outline" disabled={loading} onClick={()=>void refresh()}>
        <RefreshCw size={16}/> Atualizar pessoas
      </button>
    </div>
    {loading&&<p role="status">Carregando inventário de pessoas da operação…</p>}
    {error&&<p role="alert" className="admin-inventory__error">{error}</p>}
    {people&&<>
      <div className="admin-inventory__create-fields">
        <label htmlFor="admin-people-filter">Filtrar operadores e filas
          <input id="admin-people-filter" type="search" value={filter}
            placeholder="Nome, identificador ou fila" onChange={e=>setFilter(e.target.value)}/>
        </label>
      </div>
      <p id="admin-operators-scroll-hint" className="admin-inventory__scroll-hint">
        Tabela com rolagem horizontal: pressione Tab para focar e use as setas para acessar todas as colunas.
      </p>
      <div className="admin-inventory__table-scroll" role="region"
        aria-label="Tabela de operadores e memberships"
        aria-describedby="admin-operators-scroll-hint" tabIndex={0}>
        <table>
          <caption>Operadores da operação {people.operation.name} ({operators.length} exibidos de {people.operators.length})</caption>
          <thead><tr>
            <th scope="col">Operador</th><th scope="col">Presença</th>
            <th scope="col">Capacidade</th><th scope="col">Ofertados</th>
            <th scope="col">Ativos</th><th scope="col">Memberships (despacho)</th>
          </tr></thead>
          <tbody>{operators.map(operator=><tr key={operator.id}>
            <th scope="row"><strong>{operator.name}</strong><small>{operator.id}</small></th>
            <td>{operator.presence}</td><td>{operator.capacity}</td>
            <td>{operator.offered}</td><td>{operator.active}</td>
            <td>{operator.memberships.length
              ? operator.memberships.map(m=>m.queue_name+' ('+m.queue_id+')').join(', ')
              : 'Sem fila atribuída'}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {operators.length===0&&<EmptyState className="admin-inventory__empty">
        Nenhum operador corresponde ao filtro.</EmptyState>}
      <p id="admin-accounts-scroll-hint" className="admin-inventory__scroll-hint">
        Tabela com rolagem horizontal: pressione Tab para focar e use as setas para acessar todas as colunas.
      </p>
      <div className="admin-inventory__table-scroll" role="region"
        aria-label="Tabela de contas de autenticação"
        aria-describedby="admin-accounts-scroll-hint" tabIndex={0}>
        <table>
          <caption>Contas de autenticação da operação ({people.accounts.length}) — não representam grants</caption>
          <thead><tr>
            <th scope="col">Conta</th><th scope="col">Papel local</th>
            <th scope="col">Situação</th><th scope="col">Operador associado</th>
          </tr></thead>
          <tbody>{people.accounts.map(account=><tr key={account.id}>
            <th scope="row">{account.username}</th><td>{account.role}</td>
            <td>{account.is_active?'Ativa':'Desativada'}</td>
            <td>{account.operator_id??'Sem perfil operacional'}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {people.accounts.length===0&&<EmptyState className="admin-inventory__empty">
        Nenhuma conta na operação.</EmptyState>}
      <p>Alterações de membership, grants e auditoria administrativa estão reservadas às próximas
        etapas B1.1/B2. O inventário não autoriza novas permissões.</p>
    </>}
  </section>
}
