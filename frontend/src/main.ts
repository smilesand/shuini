import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import { registerAppIcons } from './icons'
import router from './router/index'
import { installRuntimeLogging, logRuntimeEvent } from './utils/runtimeLogger'

const app = createApp(App)

registerAppIcons(app)
installRuntimeLogging(app, router)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')

logRuntimeEvent('INFO', 'Frontend app mounted', {
	event: 'frontend-mounted',
})
