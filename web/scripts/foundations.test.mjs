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

test('SPEC-019 semantic status colors meet text contrast and focus visibility thresholds', () => {
  const pairs = [
    ['--ux-status-active-text', '--ux-status-active-bg'],
    ['--ux-status-queued-text', '--ux-status-queued-bg'],
    ['--ux-status-offered-text', '--ux-status-offered-bg'],
    ['--ux-status-closed-text', '--ux-status-closed-bg'],
    ['--ux-status-draft-text', '--ux-status-draft-bg'],
    ['--ux-status-paused-text', '--ux-status-paused-bg'],
    ['--ux-status-archived-text', '--ux-status-archived-bg'],
    ['--ux-status-available-text', '--ux-status-available-bg'],
    ['--ux-status-away-text', '--ux-status-away-bg'],
    ['--ux-status-offline-text', '--ux-status-offline-bg'],
  ]
  for (const [foreground, background] of pairs) {
    assert.ok(
      contrast(token(foreground), token(background)) >= 4.5,
      foreground + ' on ' + background + ' must meet 4.5:1',
    )
  }
  assert.ok(contrast(token('--ux-focus'), token('--ux-surface')) >= 3,
    'focus indicator must contrast with the surface')
  assert.ok(contrast(token('--ux-disabled-text'), token('--ux-disabled-bg')) >= 4.5,
    'disabled control text must meet 4.5:1')
  assert.ok(contrast(token('--ux-disabled-border'), token('--ux-disabled-bg')) >= 3,
    'disabled control boundary must meet 3:1')
  assert.match(css, /\.search-field:focus-within/)
  assert.match(css, /:where\(button, a, input, textarea, select\):focus-visible/)
  assert.match(css, /verified-history-pagination button:disabled/)
  assert.match(css, /--ux-disabled-border/)
})

test('SPEC-019 interactive text and non-text states meet contrast thresholds', () => {
  const styles = read('src/styles.css')
  assert.ok(contrast('#ffffff', token('--ux-accent')) >= 4.5)
  assert.ok(contrast('#ffffff', '#174e8d') >= 4.5)
  assert.ok(contrast('#294f71', '#ffffff') >= 4.5)
  assert.ok(contrast('#294f71', '#f0f5fa') >= 4.5)
  assert.ok(contrast('#2985ee', '#edf5ff') >= 3,
    'selected-session indicator must contrast with its selected surface')
  assert.ok(contrast('#a43d3d', '#fff0f0') >= 4.5)
  assert.ok(contrast('#9c2939', '#ffffff') >= 4.5)
  assert.ok(contrast('#20694d', '#ffffff') >= 4.5)
  assert.ok(contrast(token('--ux-selection-indicator'), '#edf5ff') >= 3)
  assert.ok(contrast(token('--ux-selection-indicator'), '#eaf4ff') >= 3)
  assert.ok(contrast(token('--ux-selection-indicator'), '#e4f0ff') >= 3)
  assert.ok(contrast(token('--ux-control-border'), token('--ux-surface')) >= 3)
  assert.ok(contrast(token('--ux-control-border'), token('--ux-surface-subtle')) >= 3)
  assert.ok(contrast(token('--ux-control-border-dark'), '#2b435c') >= 3)
  assert.ok(contrast(token('--ux-focus-dark'), '#203247') >= 3)
  assert.ok(contrast(token('--ux-focus-dark'), '#334c66') >= 3)
  assert.match(css, /\.desk-layout--compact \.desk-mobile-tabs button:disabled\s*\{[^}]*color:\s*var\(--ux-disabled-text\)[^}]*background-color:\s*var\(--ux-disabled-bg\)[^}]*border-color:\s*var\(--ux-disabled-border\)/)
  assert.match(css, /\.primary:not\(:disabled\):hover\s*\{[^}]*background:\s*#174e8d/)
  assert.match(css, /\.outline,\s*\.icon-btn\s*\{[^}]*color:\s*#294f71/)
  assert.match(styles, /\.session\.selected\{[^}]*background:#edf5ff;box-shadow:inset 3px 0 #2985ee/)
  assert.match(styles, /\.alert\{[^}]*background:#fff0f0;[^}]*color:#a43d3d/)
  assert.match(styles, /\.admin-inventory__error\{color:#9c2939/)
  assert.match(styles, /\.admin-inventory__success\{color:#20694d/)
  const controlBorderRule = css.match(
    /\.outline:not\(:disabled\),[\s\S]*?\.desk-layout--compact \.desk-mobile-tabs button:not\(:disabled\)\s*\{([^}]*)\}/,
  )?.[1]
  assert.ok(controlBorderRule)
  assert.match(controlBorderRule, /border-color:\s*var\(--ux-control-border\)/)
  assert.match(css, /\.history-ticket\.selected,[\s\S]*?\{[^}]*box-shadow:\s*inset 3px 0 var\(--ux-selection-indicator\)/)
  assert.match(css, /\.history-mode-tabs button\.active\s*\{[^}]*border-color:\s*var\(--ux-selection-indicator\)/)
  assert.match(css, /\.verified-history-detail-pages button:focus-visible,[\s\S]*?\.workspace-home__card:focus-visible\s*\{[^}]*outline-color:\s*var\(--ux-focus\)/)
  assert.match(css, /\.admin-inventory__create-fields input:focus-visible,[\s\S]*?\{[^}]*outline:\s*3px solid var\(--ux-focus\)/)
  assert.match(css, /\.admin-inventory__confirm button:focus-visible\s*\{[^}]*outline:\s*3px solid var\(--ux-focus\)/)
  assert.match(css, /\.sidebar \.nav:focus-visible,[\s\S]*?\.operator-portal__actions :focus-visible\s*\{[^}]*outline-color:\s*var\(--ux-focus-dark\)/)
})

test('SPEC-019 shared Portuguese presentation labels are explicit and do not expose raw errors', () => {
  const presentation = read('src/design-system/presentation.ts')
  for (const label of ['Na fila', 'Oferta pendente', 'Ativo', 'Encerrado',
    'Rascunho', 'Pausado', 'Arquivado', 'Disponível', 'Em pausa',
    'Indisponível', 'Administrador', 'Supervisor', 'Operador', 'Auditor',
    'Atendimento aceito', 'Oferta recusada', 'Atendimento transferido']) {
    assert.ok(presentation.includes(label), 'missing localized label ' + label)
  }
  assert.match(presentation, /export function userFacingError/)
  assert.match(presentation, /export function eventLabel/)
  assert.match(presentation, /401/)
  assert.match(presentation, /403/)
  assert.match(presentation, /404/)
  assert.match(presentation, /409/)
  assert.doesNotMatch(presentation, /error\.message/)
})
