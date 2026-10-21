import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = path => readFileSync(resolve(root, path), 'utf8')
const css = read('src/design-system/foundations.css')

function token(name) {
  const match = css.match(new RegExp('(?:^|\\n)\\s*' + name + '\\s*:\\s*(#[0-9a-fA-F]{6})\\s*;', 'm'))
  assert.ok(match, 'missing token: ' + name)
  return match[1]
}
function luminance(hex) {
  const components = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
  const [r, g, b] = components.map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
function contrast(a, b) {
  const values = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (values[0] + 0.05) / (values[1] + 0.05)
}

test('SPEC-018 U1 loads light foundations after legacy G07 style contracts', () => {
  const entry = read('src/main.tsx')
  assert.match(entry, /import '\.\/styles\.css'\s+import '\.\/design-system\/foundations\.css'/)
  assert.match(css, /color-scheme: light/)
  for (const item of ['--ux-surface', '--ux-ink', '--ux-muted', '--ux-accent', '--ux-focus',
    '--ux-line', '--ux-shadow', '--ux-space-4']) {
    assert.ok(css.includes(item), 'missing design token ' + item)
  }
  assert.match(css, /\.sidebar\s*\{[^}]*background:\s*#203247/s)
  assert.match(css, /\.workspace-home__card:hover\s*\{[^}]*transform:\s*none/s)
})

test('SPEC-018 U1 meets contrast minimums for its primary text and primary action', () => {
  assert.ok(contrast(token('--ux-ink'), token('--ux-surface')) >= 4.5)
  assert.ok(contrast(token('--ux-muted'), token('--ux-surface')) >= 4.5)
  assert.ok(contrast('#ffffff', token('--ux-accent')) >= 4.5)
  assert.ok(contrast('#d8e4f0', '#203247') >= 4.5)
})

test('SPEC-018 U1 preserves interactive G07 contracts and reduced-motion support', () => {
  const legacy = read('src/styles.css')
  const desk = read('src/OperatorDesk.tsx')
  assert.match(css, /:focus-visible/)
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/)
  assert.doesNotMatch(css, /\.offer-dialog\s*\{|\.offer-dialog__buttons\s*\{|\.desk-feedback\s*\{/)
  assert.doesNotMatch(css, /\.admin-inventory__table-scroll\s*\{|\.desk-grid\s*\{/)
  assert.match(legacy, /max-height:calc\(100dvh - 36px\)/)
  assert.match(desk, /aria-modal="true"/)
})

test('SPEC-018 U1 empty states are shared and disclose no grants or secrets', () => {
  const component = read('src/design-system/EmptyState.tsx')
  assert.match(component, /role="status"/)
  assert.doesNotMatch(component, /fetch\(|localStorage|access_token|password_hash/)
  for (const path of [
    'src/workspaces/AdminLanding.tsx',
    'src/workspaces/AdminPeople.tsx',
    'src/workspaces/SupervisorOverview.tsx',
  ]) {
    const text = read(path)
    assert.match(text, /import \{ EmptyState \} from '\.\.\/design-system\/EmptyState'/)
    assert.match(text, /<EmptyState className=/)
  }
})

test('SPEC-018 U1 keeps backend permissions, routes, lifecycle retry, and mobile release independent', () => {
  const app = read('src/App.tsx')
  const admin = read('src/workspaces/AdminLanding.tsx')
  assert.doesNotMatch(app, /['"]MONITOR['"]/)
  assert.match(admin, /expected_version:change\.version/)
  const handler = admin.match(/async function commitTransition\(\)\s*\{([\s\S]*?)\n  \}/)?.[1]
  assert.ok(handler)
  assert.equal((handler.match(/\bapi\(/g) ?? []).length, 1)
  assert.doesNotMatch(handler, /\b(retry|setInterval|setTimeout)\b/i)
})
