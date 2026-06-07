import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

import { registerPinyinEngine } from '@zh-keyboard/vue'
import { RimePinyinEngine } from '@zh-keyboard/pinyin'

registerPinyinEngine(new RimePinyinEngine({
  wasmDir: '/rime',
  dataFiles: [
    'default.yaml',
    'luna_pinyin.schema.yaml',
    'luna_pinyin.custom.table.bin',
    'luna_pinyin.custom.prism.bin',
    'luna_pinyin.custom.reverse.bin',
    'luna_pinyin.table.bin',
    'luna_pinyin.prism.bin',
    'luna_pinyin.reverse.bin',
  ],
}))

createApp(App).use(router).mount('#app')
