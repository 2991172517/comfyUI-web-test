import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router/index.js'
import { initUiFontScale } from '@/composables/useUiFontScale.js'
import './assets/index.css'

initUiFontScale()

createApp(App).use(router).mount('#app')
