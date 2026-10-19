import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (path) => readFileSync(resolve(root,path),'utf8')

test('verified events scroll without clipping paging controls and support keyboard focus', () => {
  const css = read('src/styles.css')
  const history = read('src/workspaces/ScopedVerifiedHistory.tsx')
  assert.match(css, /\.verified-history-layout \.history-events\s*\{[^}]*max-height:180px;overflow-y:auto;flex-shrink:0/)
  assert.match(css, /\.verified-history-layout \.history-details__header,\s*\.verified-history-layout \.verified-history-detail-pages\{flex-shrink:0\}/)
  assert.match(css, /\.verified-history-layout \.history-events:focus-visible\s*\{[^}]*outline:3px solid/)
  assert.match(history, /className="history-events" role="region" aria-label="Eventos comprovados" tabIndex=\{0\}/)
})

test('a POC has distinct URLs for all workspaces', () => {
  const app = read('src/App.tsx')
  for (const path of [
    '/operador',
    '/supervisao',
    '/supervisao/conversas',
    '/supervisao/filas',
    '/supervisao/equipe',
    '/laboratorio',
    '/administracao',
  ]) {
    assert.ok(app.includes('path="'+path+'"'), 'missing route '+path)
  }
  assert.match(read('src/main.tsx'), /<BrowserRouter>/)
  assert.match(app, /if\(homeMode\)return <WorkspaceHome\/>/)
  assert.ok(existsSync(resolve(root, 'src/workspaces/WorkspaceHome.tsx')))
})

test('each supervisor screen has an independent page module', () => {
  for(const page of [
    'SupervisorOverview.tsx',
    'SupervisorConversations.tsx',
    'SupervisorQueues.tsx',
    'SupervisorTeam.tsx',
    'DemoLab.tsx',
    'AdminLanding.tsx',
  ]){
    assert.ok(existsSync(resolve(root,'src/workspaces',page)),page+' missing')
  }
})

test('operator is a separate viewport-fitted workspace with internal scrolling only', () => {
  const app = read('src/App.tsx')
  const desk = read('src/OperatorDesk.tsx')
  const css = read('src/styles.css')
  assert.match(app,/if\(operatorMode\)return/)
  assert.match(app,/className="operator-portal"/)
  assert.match(app,/className="operator-portal__main"/)
  assert.match(css,/\.operator-portal__main\s*\{[\s\S]*?overflow:hidden/)
  assert.match(css,/\.operator-portal__main \.desk-grid\s*\{[\s\S]*?height:auto!important/)
  assert.match(css,/\.operator-portal__main \.desk-chat-list\s*\{[\s\S]*?overflow-y:auto/)
  assert.match(css,/\.desk-layout--compact \.desk-worklist\s*\{[\s\S]*?overflow-y:auto/)
  assert.match(desk,/className="desk-chat-tools"/)
  assert.match(desk,/setTransferOpen/)
  assert.match(desk,/e\.shiftKey/)
  assert.match(app,/if\(adminMode\)return/)
  assert.match(app,/className="layout layout--supervisor"/)
})

test('supervisor history is read-only; simulator has its own screen', () => {
  const history = read('src/workspaces/SupervisorConversations.tsx')
  assert.doesNotMatch(history,/sender:\s*['"]OPERATOR['"]/)
  assert.doesNotMatch(history,/\/messages['"],\s*['"]POST['"]/)
  const lab = read('src/workspaces/DemoLab.tsx')
  assert.match(lab,/Criar solicitação simulada/)
  assert.match(lab,/onCreate/)
})


test('RBAC client uses bearer identity rather than shared POC key', () => {
  const app=read('src/App.tsx')
  assert.match(app,/\/v1\/auth\/login/)
  assert.match(app,/Authorization.*Bearer/)
  assert.match(app,/if\(!permitted\)return/)
  assert.match(app,/\/v1\/auth\/heartbeat/)
  assert.doesNotMatch(app,/['"]X-POC-Key['"]\s*:/)
})

test('operator workspace shows a pending-offer popup without manual dispatcher', () => {
  const desk=read('src/OperatorDesk.tsx')
  const queues=read('src/workspaces/SupervisorQueues.tsx')
  assert.match(desk,/role="alertdialog"/)
  assert.match(desk,/lockedIdentity/)
  assert.match(desk,/setInterval\(poll,3000\)/)
  assert.match(queues,/Ordem atual de distribuição/)
  assert.doesNotMatch(queues,/Ofertar próximo/)
})


test('supervisor route props match the page contracts', () => {
  const app = read('src/App.tsx')
  const history = read('src/workspaces/SupervisorConversations.tsx')
  const queues = read('src/workspaces/SupervisorQueues.tsx')
  const historyRoute = app.match(/<SupervisorConversations\b([\s\S]*?)\/>/)
  const queueRoute = app.match(/<SupervisorQueues\b([\s\S]*?)\/>/)
  assert.ok(historyRoute, 'missing read-only conversations route')
  assert.ok(queueRoute, 'missing queues route')
  assert.doesNotMatch(historyRoute[1], /\bonChanged\s*=/,
    'conversation page does not accept onChanged')
  assert.match(queueRoute[1], /\bonChanged\s*=\{refresh\}/,
    'queue management requires refresh callback')
  assert.match(history, /type Props = \{tickets:Ticket\[\];api:Api;showVerified\?:boolean\}/)
  assert.match(queues, /onChanged:\(\)=>Promise<void>/)
})

test('transfer choices are independent from operator queue membership', () => {
  const desk = read('src/OperatorDesk.tsx')
  const api = read('../src/handoff_hub/operator_workflow.py')
  const auth = read('../src/handoff_hub/poc_auth.py')
  assert.match(desk,/\/transfer-targets/)
  assert.match(desk,/transferTargets\.map/)
  assert.doesNotMatch(desk,/\{queues\.map\(q=><option/)
  assert.match(desk,/transferTargets\.some\(q=>q\.id===targetQueue\)/)
  assert.match(api,/@router\.get\("\/handoffs\/\{handoff_id\}\/transfer-targets"\)/)
  assert.match(api,/Queue\.operation_id == handoff\.operation_id/)
  assert.match(api,/Queue\.id != handoff\.queue_id/)
  assert.match(auth,/transfer-targets/)
})


test('private transfer reason follows the handoff without entering user chat', () => {
  const desk = read('src/OperatorDesk.tsx')
  const workflow = read('../src/handoff_hub/operator_workflow.py')
  const css = read('src/styles.css')
  assert.match(workflow, /"reason": t\.reason/)
  assert.match(workflow, /"from_operator_name"/)
  assert.match(workflow, /"from_queue_name"/)
  assert.match(desk, /history\.transfers/)
  assert.match(desk, /offer-dialog__transfer-note/)
  assert.match(desk, /desk-handoff-note/)
  assert.match(desk, /Orientação interna recebida/)
  assert.match(desk, /Nota de transferência — não enviada ao usuário final/)
  assert.match(css, /\.desk-layout--compact \.desk-handoff-note/)
})

test('verified segment history is read-only, separate, and transparent about partial data', () => {
  const app = read('src/App.tsx')
  const history = read('src/workspaces/SupervisorConversations.tsx')
  const verified = read('src/workspaces/ScopedVerifiedHistory.tsx')
  const api = read('../src/handoff_hub/verified_history.py')
  assert.match(app, /showVerified=\{user\?\.role==='SUPERVISOR'\|\|user\?\.role==='AUDITOR'\}/)
  assert.match(history, /<ScopedVerifiedHistory api=\{api\}/)
  assert.match(history, /Segmentos verificados/)
  assert.match(verified, /\/v1\/me\/queues/)
  assert.match(verified, /\/v1\/history\/verified-sessions/)
  assert.match(verified, /\/verified-history\?queue_id=/)
  assert.match(verified, /Visualização parcial/)
  assert.match(verified, /schema_ready/)
  assert.match(api, /assigned_by == "RUNTIME"/)
  assert.doesNotMatch(verified, /'POST'|"POST"/)
  assert.doesNotMatch(verified, /transfer\.reason|\.requester_label|\.subject/)
})

test('verified history details paginate messages and events independently', () => {
  const view = read('src/workspaces/ScopedVerifiedHistory.tsx')
  const api = read('../src/handoff_hub/verified_history.py')
  assert.match(view, /const \[messagePage,setMessagePage\]/)
  assert.match(view, /const \[eventPage,setEventPage\]/)
  assert.match(view, /&message_page=/)
  assert.match(view, /&event_page=/)
  assert.match(view, /detail\.message_next_page===null/)
  assert.match(view, /detail\.event_next_page===null/)
  assert.match(view, /setMessagePage\(1\)/)
  assert.match(view, /setEventPage\(1\)/)
  assert.match(view, /Página anterior de mensagens/)
  assert.match(view, /Próxima página de eventos/)
  assert.match(api, /message_page: int = Query\(default=1, ge=1, le=1000\)/)
  assert.match(api, /event_page: int = Query\(default=1, ge=1, le=1000\)/)
  assert.match(api, /page_size: int = Query\(default=25, ge=1, le=50\)/)
  assert.match(api, /\.limit\(page_size \+ 1\)/)
  assert.doesNotMatch(view, /'POST'|"POST"/)
})


test('verified history clears sensitive view state before grant refresh', () => {
  const view = read('src/workspaces/ScopedVerifiedHistory.tsx')
  assert.match(view,/setQueues\(\[\]\);setQueueId\(''\);setListing\(null\);setSelectedId\(null\)/)
  assert.match(view,/setDetail\(null\);setError\(''\);setLoading\(false\)/)
  assert.match(view,/setGrantsLoading\(true\);setRefreshKey\(v=>v\+1\)/)
  assert.match(view,/!queueId\|\|!queues\.some\(q=>q\.id===queueId\)/)
  assert.match(view,/Não foi possível validar as filas concedidas/)
  assert.match(view,/Nenhuma fila autorizada para consulta de histórico/)
  assert.match(view,/disabled=\{grantsLoading\}/)
  assert.match(view,/preferredQueueRef\.current=queueId/)
  assert.match(view,/available\.find\(q=>q\.id===preferredQueueRef\.current\)/)
  assert.match(view,/setListing\(null\)[\s\S]*?setSelectedId\(null\)[\s\S]*?setDetail\(null\)/)
})

test('supervisor release QA displays current POC version and live-only counter semantics', () => {
  const app = read('src/App.tsx')
  const css = read('src/styles.css')
  assert.match(app, /POC 0\.5 · Sem integração Teams/)
  assert.doesNotMatch(app, /POC 0\.4 · Sem integração Teams/)
  assert.match(app, /countMeaning="Quantidade de atendimentos correntes; não inclui o histórico verificado"/)
  assert.match(css, /\.verified-history-layout \.history-details\{[\s\S]*?min-height:340px/)
  assert.match(css, /\.verified-history-layout \.history-ticket:focus-visible/)
})


test('verified paging clears stale content before fetching and labels controls', () => {
  const view = read('src/workspaces/ScopedVerifiedHistory.tsx')
  assert.match(view, /aria-pressed=\{selectedId===t\.session_id\}/)
  assert.match(view, /aria-live="polite"/)
  assert.match(view, /aria-label="Paginação de atendimentos verificados"/)
  assert.match(view, /disabled=\{loading\|\|page<=1\}/)
  assert.match(view, /disabled=\{loading\|\|listing\.next_page===null\}/)
  assert.match(view, /setListing\(null\);setLoading\(true\)/)
  assert.match(view, /setDetail\(null\);setDetailLoading\(true\);setMessagePage\(v=>v[+-]1\)/)
  assert.match(view, /setDetail\(null\);setDetailLoading\(true\);setEventPage\(v=>v[+-]1\)/)
  assert.match(view, /if\(!selectedId\|\|!queueId\)\{\s*setDetail\(null\)\s*setDetailLoading\(false\)/)
})


test('admin queue ID follows HTML Unicode v constraint and server-side format', () => {
  const page = read('src/workspaces/AdminLanding.tsx')
  const input = page.match(/<input\s+id="new-queue-id"([\s\S]*?)\/>/)
  assert.ok(input, 'queue ID input is required')
  const pattern = input[1].match(/\bpattern="([^"]+)"/)?.[1]
  assert.ok(pattern, 'HTML constraint validation pattern is required')
  assert.equal(pattern, '[a-z](?:[a-z0-9]|-){1,39}')
  const compiled = new RegExp('^(?:' + pattern + ')$', 'v')
  for (const valid of ['n3', 'suporte-n3', 'a-', 'a--', 'a'.repeat(40)]) {
    assert.equal(compiled.test(valid), true, 'expected valid ID: ' + valid)
  }
  for (const invalid of ['', 'a', 'A3', 'bad/queue', 'a_b', 'á3',
    ' a', 'a ', 'a\n3', 'a'.repeat(41)]) {
    assert.equal(compiled.test(invalid), false, 'expected invalid ID: ' + invalid)
  }
})

test('admin people inventory stays read-only and separate from role grants', () => {
  const landing=read('src/workspaces/AdminLanding.tsx')
  const people=read('src/workspaces/AdminPeople.tsx')
  assert.match(landing,/import AdminPeople from '\.\/AdminPeople'/)
  assert.match(landing,/<AdminPeople api=\{api\}\/>/)
  assert.match(people,/\/v1\/admin\/people/)
  assert.match(people,/membership_write_available/)
  assert.match(people,/grant_write_available/)
  assert.match(people,/role="alert"/)
  assert.match(people,/Operadores da operação/)
  assert.match(people,/Contas de autenticação da operação/)
  assert.doesNotMatch(people,/api\([^)]*,\s*['"](POST|PATCH|DELETE)['"]/)
})
