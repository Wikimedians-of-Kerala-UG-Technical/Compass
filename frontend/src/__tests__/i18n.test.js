import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import en from '../locales/en.json'
import { i18n } from '../i18n.js'

function keys(obj, prefix = '') {
  return Object.entries(obj).flatMap(([k, v]) => (typeof v === 'object' ? keys(v, prefix + k + '.') : [prefix + k]))
}

function sources(dir) {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f)
    if (statSync(p).isDirectory()) return f === '__tests__' ? [] : sources(p)
    return /\.(vue|js)$/.test(f) ? [p] : []
  })
}

describe('English messages', () => {
  const all = new Set(keys(en))
  const src = sources(join(__dirname, '..')).map((p) => readFileSync(p, 'utf8')).join('\n')

  it('has every key the code uses', () => {
    // Literal keys in $t('…'), t('…'), keypath="…" and label: '…'.
    const used = [...src.matchAll(/(?:\$t|\bt)\(\s*'([a-zA-Z]+\.[\w.]+)'|keypath="([\w.]+)"|label: '([a-z]+\.[\w.]+)'/g)]
      .map((m) => m[1] || m[2] || m[3])
    const missing = [...new Set(used)].filter((k) => !all.has(k))
    expect(missing).toEqual([])
  })

  it('formats placeholders and plurals', () => {
    const { t } = i18n.global
    expect(t('overview.card.tasks', 0)).toBe('No tasks ready')
    expect(t('overview.card.tasks', 1)).toBe('1 task ready')
    expect(t('overview.card.tasks', 12)).toBe('12 tasks ready')
    expect(t('tasks.minutes', { label: 'Add citations', min: 10 })).toBe('Add citations · ~10 min')
  })
})
