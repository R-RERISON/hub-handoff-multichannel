import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = (path) => readFileSync(resolve(root,path),'utf8')

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
  assert.match(history, /type Props = \{tickets:Ticket\[\];api:Api\}/)
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
