import { createI18n } from 'vue-i18n'
import en from './locales/en.json'

// Interface translations. English is the source; to add a language, copy
// locales/en.json to locales/<code>.json, translate the values (keep the {placeholders}
// and the "a | b | c" plural forms) and add it to `messages` below. The browser's
// language picks the locale, falling back to English for anything missing.
export const messages = { en }

function pickLocale() {
  const wanted = (typeof navigator !== 'undefined' && navigator.languages) || []
  for (const tag of wanted) {
    const code = tag.toLowerCase().split('-')[0]
    if (messages[code]) return code
  }
  return 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: pickLocale(),
  fallbackLocale: 'en',
  messages,
})
