import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { ArrowUpRight, CheckCircle2, LockKeyhole, Plus, RefreshCw, ServerCog, Shield } from 'lucide-react'
import type { Api } from './types'
import AdminPeople from './AdminPeople'

type QueueRow = {
  id:string
  name:string
  members:number
  grants:number
  waiting:number
  offered:number
  active:number
  total_sessions:number
  lifecycle_state:'DRAFT'|'ACTIVE'|'PAUSED'|'ARCHIVED'
  lifecycle_version:number
}
type Inventory = {
  operation:{id:string;name:string}
  summary:{queues:number;operators:number;accounts:number;role_grants:number;sessions_in_progress:number}
  queues:QueueRow[]
  capabilities:{read_only:true;queue_create_available:boolean;queue_lifecycle_available:boolean;identity_provider:'LOCAL_POC'}
}

export default function AdminLanding({api}:{api:Api}){
  const [inventory,setInventory]=useState<Inventory|null>(null)
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [newId,setNewId]=useState('')
  const [newName,setNewName]=useState('')
  const [saving,setSaving]=useState(false)
  const [createError,setCreateError]=useState('')
  const [createNotice,setCreateNotice]=useState('')
  const [selectedTransition,setSelectedTransition]=useState<{id:string;name:string;state:'ACTIVE'|'PAUSED'|'ARCHIVED';version:number}|null>(null)
  const [transitionBusy,setTransitionBusy]=useState(false)
  const [transitionError,setTransitionError]=useState('')
  const [transitionNotice,setTransitionNotice]=useState('')
  const refresh=useCallback(async ()=>{
    setLoading(true);setError('');setInventory(null)
    try{
      const result:Inventory=await api('/v1/admin/overview')
      if(!result.capabilities.read_only)throw new Error('Contrato inesperado')
      setInventory(result)
    }catch{
      setError('Inventário indisponível ou acesso não autorizado. Nenhum dado anterior foi mantido.')
    }finally{setLoading(false)}
  },[api])
  useEffect(()=>{void refresh()},[refresh])
  async function commitTransition(){
    if(!selectedTransition||transitionBusy)return
    const change=selectedTransition
    setTransitionBusy(true);setTransitionError('');setTransitionNotice('')
    try{
      const response=await api('/v1/admin/queues/'+encodeURIComponent(change.id)+'/state',
        'PATCH',{state:change.state,expected_version:change.version})
      if(response.audit!=='APPLIED'||response.state!==change.state)
        throw new Error('Estado não confirmado')
      setSelectedTransition(null)
      await refresh()
      setTransitionNotice('Alteração de estado confirmada no diário administrativo.')
    }catch{
      setSelectedTransition(null)
      setTransitionError('Alteração não aplicada. Atualize a lista e confira pendências/versão.')
      await refresh()
    }finally{setTransitionBusy(false)}
  }
  async function createQueue(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    if(saving||!inventory?.capabilities.queue_create_available)return
    setSaving(true);setCreateError('');setCreateNotice('')
    try{
      const response=await api('/v1/admin/queues','POST',{id:newId,name:newName})
      if(response.audit!=='APPLIED')throw new Error('Persistência não confirmada')
      setNewId('');setNewName('')
      await refresh()
      setCreateNotice('Fila cadastrada e auditada na operação autenticada.')
    }catch{
      setCreateError('Cadastro não confirmado. Verifique identificador, permissão e disponibilidade.')
    }finally{setSaving(false)}
  }

  return <div className="section-stack admin-inventory">
    <section className="intro-banner">
      <div>
        <span className="eyebrow">SPEC-007 / ADMINISTRAÇÃO · POC LOCAL</span>
        <h2>Operações e filas</h2>
        <p>Inventário confirmado pelo backend para a operação autenticada. Alterações de cadastro,
          permissões avançadas e regras de roteamento serão liberadas em incrementos posteriores.</p>
      </div>
      <div className="banner-icon"><ServerCog size={28}/></div>
    </section>
    <div className="admin-inventory__status">
      <span><LockKeyhole size={16}/> Inventário somente leitura · Cadastro auditado</span>
      <button className="outline" type="button" onClick={()=>void refresh()} disabled={loading}>
        <RefreshCw size={16}/> Atualizar inventário
      </button>
    </div>
    {loading&&<section className="panel admin-inventory__feedback" role="status">
      Consultando dados autorizados da operação…
    </section>}
    {error&&<section className="panel admin-inventory__feedback" role="alert">{error}</section>}
    {inventory&&<>
      <section className="panel admin-inventory__operation">
        <div><span className="eyebrow">OPERAÇÃO VINCULADA</span>
          <h3>{inventory.operation.name}</h3>
          <small>Identificador: {inventory.operation.id}</small></div>
        <span className="admin-inventory__tag"><CheckCircle2 size={15}/> Escopo validado</span>
      </section>
      <section className="admin-inventory__metrics" aria-label="Indicadores da operação">
        {([
          ['Filas','queues'],['Operadores','operators'],['Contas','accounts'],
          ['Grants de leitura','role_grants'],['Atendimentos em fluxo','sessions_in_progress'],
        ] as const).map(([label,key])=><div className="panel admin-inventory__metric" key={key}>
          <span>{label}</span><strong>{inventory.summary[key]}</strong>
        </div>)}
      </section>
      {inventory.capabilities.queue_create_available&&
        <form className="panel admin-inventory__create" onSubmit={event=>void createQueue(event)}>
          <div>
            <span className="eyebrow">SPEC-007 / A1.1 · CADASTRO AUDITÁVEL</span>
            <h3>Cadastrar fila</h3>
            <p>Identificador estável; operação vinculada ao login.
              Não concede acesso, membership nem habilita integração.</p>
          </div>
          <div className="admin-inventory__create-fields">
            <label htmlFor="new-queue-id">Identificador
              <input id="new-queue-id" required minLength={2} maxLength={40}
                pattern="[a-z](?:[a-z0-9]|-){1,39}" autoComplete="off"
                placeholder="suporte-n3" value={newId} disabled={saving}
                onChange={event=>setNewId(event.target.value)}/>
            </label>
            <label htmlFor="new-queue-name">Nome exibido
              <input id="new-queue-name" required minLength={3} maxLength={120}
                autoComplete="off" placeholder="Suporte N3"
                value={newName} disabled={saving}
                onChange={event=>setNewName(event.target.value)}/>
            </label>
            <button className="primary" type="submit" disabled={saving||loading}>
              <Plus size={15}/> {saving?'Gravando…':'Cadastrar fila'}
            </button>
          </div>
          {createError&&<p role="alert" className="admin-inventory__error">{createError}</p>}
          {createNotice&&<p role="status" className="admin-inventory__success">{createNotice}</p>}
        </form>}
      <section className="panel admin-inventory__table">
        <header><div><span className="eyebrow">CADASTRO DE FILAS</span>
          <h3>Filas da operação</h3>
          <p>Estados administrados com versionamento, auditoria e proteção das sessões em andamento.</p></div>
          <span className="admin-inventory__tag"><Shield size={15}/> Dados sem conteúdo de conversas</span>
        </header>
        <p id="admin-queues-scroll-hint" className="admin-inventory__scroll-hint">
          Tabela com rolagem horizontal: pressione Tab para focar e use as setas para acessar todas as colunas.
        </p>
        <div className="admin-inventory__table-scroll" role="region"
          aria-label="Tabela de filas da operação"
          aria-describedby="admin-queues-scroll-hint" tabIndex={0}>
          <table>
            <thead><tr><th scope="col">Fila</th><th scope="col">Membros</th>
              <th scope="col">Grants</th><th scope="col">Aguardando</th>
              <th scope="col">Ofertados</th><th scope="col">Ativos</th>
              <th scope="col">Total histórico</th><th scope="col">Estado</th>
              <th scope="col">Ações</th></tr></thead>
            <tbody>{inventory.queues.map(q=><tr key={q.id}>
              <th scope="row"><strong>{q.name}</strong><small>{q.id}</small></th>
              <td>{q.members}</td><td>{q.grants}</td><td>{q.waiting}</td>
              <td>{q.offered}</td><td>{q.active}</td><td>{q.total_sessions}</td>
              <td><span className={'admin-inventory__state admin-inventory__state--'+q.lifecycle_state.toLowerCase()}>
                {q.lifecycle_state}</span></td>
              <td>{inventory.capabilities.queue_lifecycle_available
                ? <div className="admin-inventory__state-actions">
                    {(q.lifecycle_state==='DRAFT'||q.lifecycle_state==='PAUSED')&&
                      <button type="button" disabled={transitionBusy}
                        onClick={()=>setSelectedTransition({id:q.id,name:q.name,state:'ACTIVE',version:q.lifecycle_version})}>Ativar</button>}
                    {q.lifecycle_state==='ACTIVE'&&
                      <button type="button" disabled={transitionBusy}
                        onClick={()=>setSelectedTransition({id:q.id,name:q.name,state:'PAUSED',version:q.lifecycle_version})}>Pausar</button>}
                    {(q.lifecycle_state==='DRAFT'||q.lifecycle_state==='PAUSED')&&
                      <button type="button" disabled={transitionBusy}
                        onClick={()=>setSelectedTransition({id:q.id,name:q.name,state:'ARCHIVED',version:q.lifecycle_version})}>Arquivar</button>}
                  </div>
                : <span aria-label="Ciclo de vida indisponível">—</span>}</td>
            </tr>)}</tbody>
          </table>
        </div>
        {inventory.queues.length===0&&<p className="admin-inventory__empty">
          Nenhuma fila registrada nesta operação.</p>}
      </section>
      {selectedTransition&&<section className="panel admin-inventory__confirm" role="group"
        aria-label="Confirmar mudança de estado">
        <div><strong>Confirmar {selectedTransition.state} — {selectedTransition.name}?</strong>
          <p>Uma pausa/arquivamento será recusada se existirem atendimentos pendentes,
             ofertados ou ativos. Arquivamento é irreversível nesta fase.</p></div>
        <div className="admin-inventory__confirm-buttons">
          <button type="button" disabled={transitionBusy}
            onClick={()=>setSelectedTransition(null)}>Cancelar</button>
          <button className="primary" type="button" disabled={transitionBusy}
            onClick={()=>void commitTransition()}>{transitionBusy?'Salvando…':'Confirmar mudança'}</button>
        </div>
      </section>}
      {transitionError&&<p role="alert" className="admin-inventory__error">{transitionError}</p>}
      {transitionNotice&&<p role="status" className="admin-inventory__success">{transitionNotice}</p>}
    </>}
    <AdminPeople api={api}/>
    <section className="panel admin-inventory__next">
      <ArrowUpRight size={18}/><div><strong>Próximo incremento: gestão auditada de memberships e grants</strong>
        <p>Ciclo de vida protegido quando o schema 007a2 está habilitado.
          Próximas etapas: memberships, grants e políticas de roteamento.</p></div>
    </section>
  </div>
}
