import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import TextInput from '@/views/TextInput.vue'
import ConnectPage from '@/views/ConnectPage.vue'
import ConfigPage from '@/views/ConfigPage.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'text-input', component: TextInput },
  { path: '/connect', name: 'share', component: ConnectPage },
  { path: '/config', name: 'config', component: ConfigPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
