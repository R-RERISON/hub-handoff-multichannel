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

test('operator is in a dedicated shell with scrollable content', () => {
  const app = read('src/App.tsx')
  const css = read('src/styles.css')
  assert.match(app,/if\(operatorMode\)return/)
  assert.match(app,/className="operator-portal"/)
  assert.match(app,/className="operator-portal__main"/)
  assert.match(css,/\.operator-portal__main\s*\{[^}]*overflow-y:auto/s)
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
