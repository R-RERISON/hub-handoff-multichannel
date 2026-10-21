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

test('RC-001 G07 keeps notification action visible at 200% zoom', () => {
  const css = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  assert.match(desk, /className="outline small desk-notification-button"/)
  assert.match(desk, /Ativar alertas/)
  assert.doesNotMatch(css,
    /\.desk-layout--compact \.desk-notification-button\s*\{\s*display:\s*none/)
  assert.match(css,
    /@media\(max-width:780px\)\{[\s\S]*?\.desk-layout--compact \.desk-notification-button\s*\{\s*display:inline-flex/)
  assert.match(css,
    /\.operator-portal__main \.desk-top\s*\{min-height:0;max-height:none\}/)
})

test('RC-001 G07 enables keyboard scrolling of all three admin tables', () => {
  const css = read('src/styles.css')
  const people = read('src/workspaces/AdminPeople.tsx')
  const landing = read('src/workspaces/AdminLanding.tsx')
  const regions = [
    ['admin-operators-scroll-hint', 'Tabela de operadores e memberships', people],
    ['admin-accounts-scroll-hint', 'Tabela de contas de autenticação', people],
    ['admin-queues-scroll-hint', 'Tabela de filas da operação', landing],
  ]
  for (const [hintId, label, content] of regions) {
    assert.ok(content.includes('id="' + hintId + '"'), 'missing hint: ' + hintId)
    assert.ok(content.includes('aria-label="' + label + '"'), 'missing region: ' + label)
    assert.ok(content.includes('aria-describedby="' + hintId + '" tabIndex={0}'),
      'missing keyboard focus: ' + label)
  }
  assert.equal((people.match(/tabIndex=\{0\}/g) ?? []).length, 2)
  assert.equal((landing.match(/tabIndex=\{0\}/g) ?? []).length, 1)
  assert.match(css, /\.admin-inventory__table-scroll:focus-visible\s*\{/)
  assert.match(css, /\.admin-inventory__table-scroll\s*\{\s*overflow-x:auto/)
  assert.match(css, /\.admin-inventory__table table\s*\{min-width:1040px\}/)
})

test('RC-001 G07 #53 prevents feedback from intercepting operational controls', () => {
  const css = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  const rule = css.match(/\.desk-layout--compact \.desk-feedback\s*\{([^}]*)\}/)?.[1]
  assert.ok(rule, 'compact desk feedback rule missing')
  assert.match(rule, /position:static/)
  assert.match(rule, /display:flex;flex:0 0 auto;flex-direction:column/)
  assert.match(rule, /max-height:min\(160px,28dvh\)/)
  assert.match(rule, /overflow-y:auto/)
  assert.doesNotMatch(rule, /position:\s*(absolute|fixed|sticky)/)
  assert.doesNotMatch(rule, /(?:^|;)\s*(top|right|bottom|left)\s*:/)
  assert.doesNotMatch(rule, /pointer-events/)
  const messageRule = css.match(/\.desk-layout--compact \.desk-feedback>\*\s*\{([^}]*)\}/)?.[1]
  assert.ok(messageRule, 'status/error messages need their own in-flow style')
  assert.match(messageRule, /flex:0 0 auto/)
  assert.doesNotMatch(messageRule, /pointer-events/)
  assert.match(desk, /className="desk-feedback" aria-live="polite"/)
  assert.match(desk, /className="notice" role="status"/)
  assert.match(desk, /aria-label="Dispensar aviso"/)
  assert.match(desk, /onClick=\{\(\)=>setNotice\(''\)\}/)
  assert.match(desk, /className="primary small"[^>]*onClick=\{\(\)=>void execute/)
})

test('RC-001 G07 #53 preserves keyboard access to dismissal and existing zoom fixes', () => {
  const css = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  assert.match(css, /\.desk-layout--compact \.desk-feedback button:focus-visible\s*\{/)
  assert.match(css, /\.desk-layout--compact \.desk-feedback:empty\{display:none\}/)
  assert.match(css, /\.desk-layout--compact \.desk-notification-button\s*\{\s*display:inline-flex/)
  assert.match(desk, /<button aria-label="Dispensar aviso" onClick=\{\(\)=>setNotice\(''\)\}>/)
})

test('RC-001 G07 #54 keeps offer actions inside a height-constrained dialog', () => {
  const css = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  const dialogRule = css.match(/\.offer-dialog\s*\{([^}]*)\}/)?.[1]
  const bodyRule = css.match(/\.offer-dialog__body\s*\{([^}]*)\}/)?.[1]
  const actionsRule = css.match(/\.offer-dialog__buttons\s*\{([^}]*)\}/)?.[1]
  assert.ok(dialogRule, 'offer dialog styles missing')
  assert.ok(bodyRule, 'offer details scrolling styles missing')
  assert.ok(actionsRule, 'offer action footer styles missing')
  assert.match(dialogRule, /max-height:calc\(100dvh - 36px\)/)
  assert.match(dialogRule, /display:flex;flex-direction:column;overflow:hidden/)
  assert.match(bodyRule, /flex:1 1 auto;min-height:0;overflow-y:auto/)
  assert.match(actionsRule, /flex:0 0 auto/)
  assert.match(desk, /className="offer-dialog" role="alertdialog" aria-modal="true"/)
  assert.match(desk, /className="offer-dialog__body" role="region"/)
  assert.match(desk, /aria-label="Detalhes da oferta" tabIndex=\{0\}/)
  assert.match(desk, /<\/div>\s*<div className="offer-dialog__buttons">/)
  assert.match(desk, /ref=\{acceptButtonRef\} className="primary"/)
  assert.match(desk, /Recusar<\/button>/)
  assert.match(desk, /Aceitar atendimento<\/button>/)
})

test('RC-001 G07 #54 preserves zoom, keyboard scrolling and transfer context', () => {
  const css = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  assert.match(css, /\.offer-overlay\{position:fixed;inset:0/)
  assert.match(css, /\.offer-dialog__body:focus-visible\s*\{/)
  assert.match(css, /\.offer-dialog__buttons button:focus-visible\s*\{/)
  assert.match(css, /@media\(max-width:700px\)\{[\s\S]*?\.offer-dialog__buttons\{flex-direction:column\}/)
  assert.match(css, /\.offer-dialog__transfer-note\{margin-top:12px;max-height:170px;overflow:auto\}/)
  assert.match(desk, /className="offer-dialog__transfer-note" role="note"/)
  assert.match(desk, /className="offer-dialog__hint"/)
  assert.match(desk, /acceptButtonRef\.current\?\.focus\(\)/)
})

test('RC-001 operation QA lab login explains temporary credentials without secrets', () => {
  const app = read('src/App.tsx')
  assert.match(app, /No laboratório, elas ficam exclusivamente no diretório TEMP/)
  assert.match(app, /ambiente iniciado pelo launcher/)
  assert.doesNotMatch(app, /Credenciais geradas em data\/demo-credentials\.txt/)
  assert.match(app, /POC local sem SSO/)
})

test('issue #58 lifecycle confirmation does not retry a state mutation', () => {
  const page = read('src/workspaces/AdminLanding.tsx')
  const transition = page.match(
    /async function commitTransition\(\)\s*\{([\s\S]*?)\n  \}/,
  )?.[1]
  assert.ok(transition, 'lifecycle transition handler is required')
  assert.match(transition, /if\(!selectedTransition\|\|transitionBusy\)return/)
  assert.match(transition, /expected_version:change\.version/)
  assert.equal((transition.match(/\bapi\(/g) ?? []).length, 1)
  assert.doesNotMatch(transition, /\b(retry|setTimeout|setInterval)\b/i)
})
