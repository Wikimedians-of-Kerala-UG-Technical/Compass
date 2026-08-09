import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@wikimedia/codex/dist/codex.style.css'
import './style.css'
import App from './App.vue'

createApp(App).use(createPinia()).mount('#app')
