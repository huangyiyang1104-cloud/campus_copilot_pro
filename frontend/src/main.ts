import { createApp } from 'vue'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import '@/styles/index.css'
import App from '@/App.vue'
import router from '@/router'
import pinia from '@/stores'

// Element Plus 暗色主题
document.documentElement.classList.add('dark')

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
