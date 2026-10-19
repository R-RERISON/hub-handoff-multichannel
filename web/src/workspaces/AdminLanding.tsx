import { useCallback, useEffect, useState } from 'react'
import { ArrowUpRight, CheckCircle2, LockKeyhole, RefreshCw, ServerCog, Shield } from 'lucide-react'
import type { Api } from './types'

type QueueRow = {
  id:string
  name:string
  members:number
  grants:number
  waiting:number
  offered:number
  active:number
  total_sessions:number
}
type Inventory = {
  operation:{id:string;name:string}
  summary:{queues:number;operators:number;accounts:number;role_grants:number;sessions_in_progress:number}
  queues:QueueRow[]
  capabilities:{read_only:true;queue_lifecycle_available:false;identity_provider:'LOCAL_POC'}
}

export default function AdminLanding({api}:{api:Api}){
  const [inventory,setInventory]=useState<Inventory|null>(null)
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
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

  return <div className="section-stack admin-inventory">
    <section className="intro-banner">
      <div>
        <span className="eyebrow">SPEC-007 / ADMINISTRAÇÃO · POC LOCAL</span>
        <h2>Operações e filas</h2>
        <p>Inventário confirmado pelo backend para a operação autenticada. Alterações de cadastro,
          pausa, arquivamento e permissões serão liberadas em incrementos posteriores.</p>
      </div>
      <div className="banner-icon"><ServerCog size={28}/></div>
    </section>
    <div className="admin-inventory__status">
      <span><LockKeyhole size={16}/> Somente leitura · Administração</span>
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
      <section className="panel admin-inventory__table">
        <header><div><span className="eyebrow">CADASTRO DE FILAS</span>
          <h3>Filas da operação</h3>
          <p>Capacidade e políticas de ciclo de vida ainda não são editáveis nesta fatia.</p></div>
          <span className="admin-inventory__tag"><Shield size={15}/> Dados sem conteúdo de conversas</span>
        </header>
        <div className="admin-inventory__table-scroll">
          <table>
            <thead><tr><th scope="col">Fila</th><th scope="col">Membros</th>
              <th scope="col">Grants</th><th scope="col">Aguardando</th>
              <th scope="col">Ofertados</th><th scope="col">Ativos</th>
              <th scope="col">Total histórico</th></tr></thead>
            <tbody>{inventory.queues.map(q=><tr key={q.id}>
              <th scope="row"><strong>{q.name}</strong><small>{q.id}</small></th>
              <td>{q.members}</td><td>{q.grants}</td><td>{q.waiting}</td>
              <td>{q.offered}</td><td>{q.active}</td><td>{q.total_sessions}</td>
            </tr>)}</tbody>
          </table>
        </div>
        {inventory.queues.length===0&&<p className="admin-inventory__empty">
          Nenhuma fila registrada nesta operação.</p>}
      </section>
    </>}
    <section className="panel admin-inventory__next">
      <ArrowUpRight size={18}/><div><strong>Próximo incremento: ciclo de vida</strong>
        <p>Cadastro, ativação, pausa e arquivamento com auditoria transacional e proteção
          contra sessões em andamento. Esta tela não executa mudanças.</p></div>
    </section>
  </div>
}
