import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import 'vite/modulepreload-polyfill'

// import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
// ModuleRegistry.registerModules([AllCommunityModule])

import {
  ModuleRegistry,
  ColumnAutoSizeModule,
  RowStyleModule,
  CellStyleModule,
  QuickFilterModule,
  TextEditorModule,
  CustomEditorModule,
  GridStateModule,
  ColumnApiModule,
  RowApiModule,
  CellApiModule,
  ScrollApiModule,
  RenderApiModule,
  EventApiModule,
  ClientSideRowModelApiModule,
  ClientSideRowModelModule,
  // ValidationModule,
} from 'ag-grid-community'

ModuleRegistry.registerModules([
  ColumnAutoSizeModule,
  RowStyleModule,
  CellStyleModule,
  QuickFilterModule,
  TextEditorModule,
  CustomEditorModule,
  GridStateModule,
  ColumnApiModule,
  RowApiModule,
  CellApiModule,
  ScrollApiModule,
  RenderApiModule,
  EventApiModule,
  ClientSideRowModelApiModule,
  ClientSideRowModelModule,
  // ValidationModule,
])

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
