import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import 'vite/modulepreload-polyfill'

import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
// TODO: Only register modules we actually use, see
//       https://www.ag-grid.com/vue-data-grid/modules/
ModuleRegistry.registerModules([AllCommunityModule])

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
