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
  assert.match(app, /if\(homeMode\)return <WorkspaceHome onLogout=\{\(\)=>void logout\(\)\}\/>/)
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
    ['admin-operators-scroll-hint', 'Tabela de operadores e vínculos de despacho', people],
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
  assert.match(transition, /if\(!selectedTransition\|\|transitionRequestRef\.current\)return/)
  assert.match(transition, /expected_version:change\.version/)
  assert.equal((transition.match(/\bapi\(/g) ?? []).length, 1)
  assert.doesNotMatch(transition, /\b(retry|setTimeout|setInterval)\b/i)
})

test('offer dialog traps keyboard focus and provides a return target', () => {
  const desk = read('src/OperatorDesk.tsx')
  assert.match(desk, /const offerBodyRef\s*=\s*useRef<HTMLDivElement\|null>\(null\)/)
  assert.match(desk, /const declineButtonRef\s*=\s*useRef<HTMLButtonElement\|null>\(null\)/)
  assert.match(desk, /ref=\{offerBodyRef\}/)
  assert.match(desk, /ref=\{declineButtonRef\}/)
  assert.match(desk, /event\.shiftKey&&document\.activeElement===first/)
  assert.match(desk, /!event\.shiftKey&&document\.activeElement===last/)
  assert.match(desk, /if\(busy\|\|offerTransferState==='loading'\|\|offerTransferState==='idle'\)offerBodyRef\.current\?\.focus\(\)/)
  assert.match(desk, /focusAfterSelectionRef\.current=select\?'composer':'worklist'/)
  assert.match(desk, /worklistHeadingRef\.current\?\.focus\(\)/)
})

test('operator mutations are single-flight and report unconfirmed outcomes safely', () => {
  const desk = read('src/OperatorDesk.tsx')
  const execute = desk.match(/async function execute\([\s\S]*?\n  \}/)?.[0]
  const reload = desk.match(/const reload = useCallback\([\s\S]*?\n  \},\[operatorId,api\]\)/)?.[0]
  const send = desk.match(/async function sendMessage\([\s\S]*?\n  \}/)?.[0]
  assert.ok(execute, 'operator mutation executor is required')
  assert.ok(reload, 'operator work refresh must serialize overlapping polls')
  assert.ok(send, 'operator message handler is required')
  assert.match(execute, /operationLockRef\.current/)
  assert.equal((execute.match(/await action\(\)/g) ?? []).length, 1)
  assert.match(execute, /await reload\(true\)/)
  assert.match(reload, /if\(workRequestPendingRef\.current&&!force\)return false/)
  assert.match(execute, /Resultado não confirmado/)
  assert.match(execute, /ação foi confirmada/)
  assert.equal((send.match(/api\(/g) ?? []).length, 1,
    'message submission must not issue a second request as a retry')
})

test('operator conversation clears prior messages while the next authorized detail loads', () => {
  const desk = read('src/OperatorDesk.tsx')
  const detailEffect = desk.match(
    /useEffect\(\(\)=>\{\s*if\(!selectedId\)[\s\S]*?\},\[selectedId,api,onChanged\]\)/,
  )?.[0]
  assert.ok(detailEffect, 'selected conversation fetch effect is required')
  assert.match(detailEffect, /setMessages\(\[\]\)/)
  assert.match(detailEffect, /setConversationLoading\(true\)/)
  assert.match(detailEffect, /setSelectedId\(null\)/)
  assert.match(detailEffect, /setNeedsReconciliation\(true\)/)
  assert.match(desk, /conversationLoading&&<div className="empty" role="status">/)
  assert.match(desk, /!conversationLoading&&!messages\.length/)
})

test('snapshot refresh ignores stale responses and clears protected data on failure', () => {
  const app = read('src/App.tsx')
  assert.match(app, /const snapshotRequestRef\s*=\s*useRef\(0\)/)
  assert.match(app, /const requestId=\+\+snapshotRequestRef\.current/)
  assert.match(app, /if\(requestId!==snapshotRequestRef\.current\)return/)
  assert.match(app, /setSnapshot\(EMPTY_SNAPSHOT\)/)
  assert.match(app, /snapshotUnavailable/)
  assert.match(app, /status===401/)
  assert.match(app, /status===403/)
  assert.match(app, /if\(e instanceof ApiError&&\(e\.status===401\|\|e\.status===403\)\)\{\s*void refresh\(\)/)
})

test('supervisor conversation details distinguish loading, empty, denied, and stale scopes', () => {
  const view = read('src/workspaces/SupervisorConversations.tsx')
  assert.match(view, /const \[detailLoading,setDetailLoading\]\s*=\s*useState\(false\)/)
  assert.match(view, /setMessages\(\[\]\)[\s\S]*?setTimeline\(null\)[\s\S]*?setDetailLoading\(true\)/)
  assert.match(view, /finally\(\(\)=>\{if\(!cancelled\)setDetailLoading\(false\)\}\)/)
  assert.match(view, /!detailLoading&&messages\.length===0/)
  assert.match(view, /tickets\.some\((?:t|ticket)=>(?:t|ticket)\.id===selectedId\)/)
  assert.match(view, /if\(selectedId===t\.id\)return/)
  assert.match(view, /Não foi possível carregar/)
})

test('admin CAS lifecycle actions use a synchronous single-flight guard', () => {
  const page = read('src/workspaces/AdminLanding.tsx')
  const transition = page.match(
    /async function commitTransition\(\)\s*\{([\s\S]*?)\n  \}/,
  )?.[1]
  assert.ok(transition, 'lifecycle transition handler is required')
  assert.match(page, /const transitionRequestRef=useRef\(false\)/)
  assert.match(transition, /transitionRequestRef\.current/)
  assert.match(transition, /expected_version:change\.version/)
  assert.match(transition, /Resultado não confirmado/)
  assert.equal((transition.match(/\bapi\(/g) ?? []).length, 1)
})

test('verified history clears every protected scope on authorization revocation', () => {
  const view = read('src/workspaces/ScopedVerifiedHistory.tsx')
  assert.match(view, /import \{ ApiError,/)
  assert.match(view, /error instanceof ApiError&&\[401,403\]\.includes\(error\.status\)/)
  assert.match(view, /setQueues\(\[\]\)[\s\S]*?setQueueId\(''\)[\s\S]*?setListing\(null\)[\s\S]*?setSelectedId\(null\)/)
  assert.match(view, /if\(selectedId===t\.session_id\)return/)
  assert.match(view, /A concessão foi revogada ou expirou/)
})

test('admin queue creation stacks and constrains controls on narrow mobile viewports', () => {
  const css = read('src/design-system/foundations.css')
  const mobile = css.match(/@media \(max-width:\s*600px\) \{([\s\S]*?)\n\}/)?.[1]
  assert.ok(mobile, 'mobile queue form layout rule is required')
  assert.match(mobile, /\.admin-inventory__create-fields\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/)
  assert.match(mobile, /\.admin-inventory__create-fields\s*>\s*button\s*\{[^}]*width:\s*100%/)
  assert.match(mobile, /white-space:\s*normal/)
  assert.match(mobile, /max-width:\s*100%/)
})

test('SPEC-019 login and compact navigation stay semantic without widening role access', () => {
  const app = read('src/App.tsx')
  const home = read('src/workspaces/WorkspaceHome.tsx')
  const css = read('src/design-system/foundations.css')
  assert.match(app, /<form\b[^>]*onSubmit=/)
  assert.match(app, /type="submit"/)
  assert.match(app, /role="alert" aria-live="assertive"/)
  assert.match(app, /<main\b/)
  assert.match(app, /aria-label=\{label\}/)
  assert.match(app, /title=\{label\}/)
  assert.match(css, /\.sidebar \.nav\[aria-label\]:focus-visible::after/)
  assert.match(app, /data-page-focus/)
  assert.match(app, /user\?\.role==='ADMIN'&&/)
  assert.match(app, /user\?\.role!=='AUDITOR'&&/)
  assert.match(home, /<main className="workspace-home"/)
  assert.match(home, /onClick=\{onLogout\}>Sair/)
  assert.match(app, /user\.role==='OPERATOR' && operatorMode/)
  assert.match(app, /user\.role==='AUDITOR'/)
  for (const path of ['/operador', '/supervisao', '/supervisao/conversas',
    '/supervisao/filas', '/supervisao/equipe', '/administracao', '/laboratorio']) {
    assert.ok(app.includes('path="'+path+'"'), 'route must remain unchanged: '+path)
  }
})

test('SPEC-019 operator polling clears denied content and labels transient stale data', () => {
  const desk = read('src/OperatorDesk.tsx')
  assert.match(desk, /import \{ ApiError \}/)
  assert.match(desk, /conversationStale/)
  assert.match(desk, /e instanceof ApiError&&\[401,403,404\]\.includes\(e\.status\)/)
  assert.match(desk, /setMessages\(\[\]\)[\s\S]*?setTimeline\(\[\]\)[\s\S]*?setTransferNotes\(\[\]\)/)
  assert.match(desk, /setConversationStale\(true\)/)
  assert.match(desk, /Conversa desatualizada/)
  assert.match(desk, /disabled=\{[^}]*conversationStale/)
  assert.match(desk, /No Teams|NÃO ENVIADA AO TEAMS/)
})

test('SPEC-019 offer guidance exposes loading, empty, unavailable, and available states', () => {
  const desk = read('src/OperatorDesk.tsx')
  assert.match(desk, /offerTransferState/)
  assert.match(desk, /loading/)
  assert.match(desk, /unavailable/)
  assert.match(desk, /role="status" aria-live="polite"/)
  assert.match(desk, /setOfferTransferState\(note\?'ready':'empty'\)/)
  assert.match(desk, /offerTransferState==='empty'/)
  assert.match(desk, /offerTransferState==='unavailable'/)
})

test('SPEC-019 queue rotation distinguishes loading, empty, stale, denied, and confirmation states', () => {
  const queues = read('src/workspaces/SupervisorQueues.tsx')
  assert.match(queues, /import \{ ApiError,/)
  assert.match(queues, /requestVersionRef/)
  assert.match(queues, /rotationState/)
  assert.match(queues, /denied/)
  assert.match(queues, /stale/)
  assert.match(queues, /<ConfirmDialog/)
  assert.match(read('src/design-system/ConfirmDialog.tsx'), /role="alertdialog"/)
  assert.match(queues, /aria-live="polite"/)
  assert.match(queues, /Não há operadores associados/)
})

test('SPEC-019 queue membership outcomes focus persistent accessible feedback', () => {
  const queues = read('src/workspaces/SupervisorQueues.tsx')
  assert.match(queues, /membershipErrorRef/)
  assert.match(queues, /membershipNoticeRef/)
  assert.match(queues, /if\(error\)membershipErrorRef\.current\?\.focus\(\)\s*else if\(notice\)membershipNoticeRef\.current\?\.focus\(\)/)
  assert.match(queues, /role="alert" tabIndex=\{-1\} data-page-focus\s*ref=\{membershipErrorRef\}/)
  assert.match(queues, /role="status"[^>]*tabIndex=\{-1\}[^>]*data-page-focus\s*ref=\{membershipNoticeRef\}/)
})

test('SPEC-019 team changes use semantic table headers and confirmation before mutation', () => {
  const team = read('src/workspaces/SupervisorTeam.tsx')
  const css = read('src/design-system/foundations.css')
  assert.match(team, /<table\b/)
  assert.match(team, /<caption>/)
  assert.match(team, /<th scope="col">/)
  assert.match(team, /<th scope="row">/)
  assert.match(team, /aria-describedby="team-table-scroll-hint"/)
  assert.match(team, /pendingChange/)
  assert.match(team, /onPresence\(/)
  assert.match(team, /onCapacity\(/)
  assert.match(team, /<ConfirmDialog/)
  assert.match(css, /\.team-table__scroll\s*\{[^}]*contain:\s*paint/)
  assert.doesNotMatch(team, /onChange=\{e=>void onPresence/)
  assert.doesNotMatch(team, /onChange=\{e=>void onCapacity/)
})

test('SPEC-019 lifecycle confirmation receives focus and announces its target', () => {
  const admin = read('src/workspaces/AdminLanding.tsx')
  const dialog = read('src/design-system/ConfirmDialog.tsx')
  assert.match(admin, /<ConfirmDialog/)
  assert.match(admin, /transitionLabels\[selectedTransition\.state\]\.noun/)
  assert.match(admin, /O arquivamento é irreversível/)
  assert.match(dialog, /role="alertdialog"/)
  assert.match(dialog, /showModal\(\)/)
  assert.match(dialog, /cancelRef\.current\?\.focus\(\)/)
  assert.match(dialog, /event\.key !== 'Tab'/)
  assert.match(dialog, /focusable\[nextIndex\]\.focus\(\)/)
  assert.match(admin, /userFacingError/)
  const transition = admin.match(/async function commitTransition\(\)\s*\{([\s\S]*?)\n  \}/)?.[1]
  assert.ok(transition)
  assert.equal((transition.match(/\bapi\(/g) ?? []).length, 1)
})

test('SPEC-019 lifecycle outcomes restore focus to persistent accessible feedback', () => {
  const admin = read('src/workspaces/AdminLanding.tsx')
  assert.match(admin, /transitionFeedbackRef/)
  assert.match(admin, /if\(transitionError\|\|transitionNotice\)transitionFeedbackRef\.current\?\.focus\(\)/)
  assert.match(admin, /role="alert" tabIndex=\{-1\} data-page-focus ref=\{transitionFeedbackRef\}/)
  assert.match(admin, /role="status" tabIndex=\{-1\} data-page-focus ref=\{transitionFeedbackRef\}/)
  assert.ok(admin.indexOf('{transitionError&&<p') < admin.indexOf('{inventory&&<>'),
    'lifecycle feedback must remain mounted while inventory refreshes')
})

test('SPEC-019 administration tables identify rows, columns, targets, and scope', () => {
  const admin = read('src/workspaces/AdminLanding.tsx')
  const people = read('src/workspaces/AdminPeople.tsx')
  assert.match(admin, /<caption>Filas da operação/)
  assert.match(admin, /<th scope="col">Fila/)
  assert.match(admin, /<th scope="row">/)
  assert.match(admin, /aria-label=\{'Pausar fila '\+q\.name\}/)
  assert.match(people, /<caption>Operadores da operação/)
  assert.match(people, /<caption>Contas de autenticação/)
  assert.match(people, /<th scope="row">/)
})

test('SPEC-019 confirmed admin queue mutations refresh shared workspace data', () => {
  const app = read('src/App.tsx')
  const admin = read('src/workspaces/AdminLanding.tsx')
  assert.match(app, /<AdminLanding api=\{api\} onChanged=\{refresh\}\/>/)
  const transition = admin.match(/async function commitTransition\(\)\s*\{([\s\S]*?)\n  \}/)?.[1]
  const create = admin.match(/async function createQueue\([\s\S]*?\n  \}/)?.[0]
  assert.ok(transition)
  assert.ok(create)
  assert.match(transition, /await onChanged\(\)/)
  assert.match(create, /await onChanged\(\)/)
})

test('SPEC-019 statuses, roles, errors, and POC capability copy are consistent', () => {
  const presentation = read('src/design-system/presentation.ts')
  for (const path of [
    'src/OperatorDesk.tsx',
    'src/workspaces/SupervisorConversations.tsx',
    'src/workspaces/SupervisorOverview.tsx',
    'src/workspaces/ScopedVerifiedHistory.tsx',
    'src/workspaces/SupervisorQueues.tsx',
    'src/workspaces/SupervisorTeam.tsx',
    'src/workspaces/AdminLanding.tsx',
    'src/workspaces/AdminPeople.tsx',
  ]) {
    assert.match(read(path), /queueStateLabel|presenceLabel|roleLabel|userFacingError/,
      'localized presentation helper not used in '+path)
  }
  assert.match(presentation, /export function queueStateLabel/)
  assert.match(presentation, /export function presenceLabel/)
  assert.match(presentation, /export function roleLabel/)
  assert.match(presentation, /export function eventLabel/)
  const overview = read('src/workspaces/SupervisorOverview.tsx')
  assert.doesNotMatch(overview, /<b>Ativos<\/b>/)
  assert.match(overview, /sem monitoramento em tempo real/i)
  assert.doesNotMatch(overview, /todos os bots integrados/i)
  const home = read('src/workspaces/WorkspaceHome.tsx')
  assert.doesNotMatch(home, /Bots, operações, permissões e políticas do produto/)
})
