import { createApp } from 'vue'
import { createPinia } from 'pinia'
// Codex's components carry their own fallbacks, but the app's CSS uses the design tokens
// directly, so the light tokens are loaded here (theme.js adds the dark ones).
import '@wikimedia/codex-design-tokens/dist/theme-wikimedia-ui-root.css'
import '@wikimedia/codex/dist/codex.style.css'
import './style.css'
import App from './App.vue'
import { router } from './router.js'
import { i18n } from './i18n.js'
import { installTheme } from './theme.js'

installTheme()
createApp(App).use(createPinia()).use(router).use(i18n).mount('#app')
