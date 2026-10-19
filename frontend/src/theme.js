// Dark mode with Codex's own dark design tokens. Codex ships them as one `:root { … }`
// block; it is applied twice: under `prefers-color-scheme: dark` (unless the viewer
// chose light) and under an explicit `data-theme="dark"`.
import darkTokens from '@wikimedia/codex-design-tokens/dist/theme-wikimedia-ui-mode-dark.css?raw'

const KEY = 'compass-theme'

export function installTheme() {
  const body = darkTokens.slice(darkTokens.indexOf('{') + 1, darkTokens.lastIndexOf('}'))
  const style = document.createElement('style')
  style.dataset.compass = 'dark-tokens'
  style.textContent =
    `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {${body}} }\n` +
    `:root[data-theme="dark"] {${body}}`
  document.head.appendChild(style)
  applyTheme(getTheme())
}

export function getTheme() {
  try {
    return localStorage.getItem(KEY) || 'auto'
  } catch {
    return 'auto'
  }
}

export function setTheme(theme) {
  try {
    if (theme === 'auto') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, theme)
  } catch {
    /* private mode: the choice lasts until reload */
  }
  applyTheme(theme)
}

function applyTheme(theme) {
  if (theme === 'auto') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = theme
}
