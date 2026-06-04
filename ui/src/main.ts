import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import { registerPinyinEngine } from '@zh-keyboard/vue'
import { RimePinyinEngine } from '@zh-keyboard/pinyin'

registerPinyinEngine(new RimePinyinEngine({ wasmDir: '/rime' }))

createApp(App).use(router).mount('#app')
