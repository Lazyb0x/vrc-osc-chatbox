<script setup lang="ts">
import {
  NButton,
  NCard,
  NDynamicTags,
  NSpace,
  NInput,
  NGrid,
  NGridItem,
  darkTheme,
  NConfigProvider,
  NInputNumber,
  NSwitch,
  NForm,
  NFormItem,
  NScrollbar,
  NLog,
} from 'naive-ui'
import type { InputInst, GlobalTheme } from 'naive-ui'
import { ref, shallowRef, onMounted, onUnmounted, watch } from 'vue'

const inputValue = ref('')
const MAX_INPUT_LENGTH = 200

const inputInstRef = ref<InputInst | null>(null)
const history = ref<string[]>([])
const ws = ref<WebSocket | null>(null)
const realTimeActive = ref(false)
const autoCutActive = ref(false)
const translationActive = ref(false)
const cutCount = ref(2)
const currText = shallowRef('')
const isCompositing = ref(false)
const translationLanguages = ref(['en'])

const theme = ref<GlobalTheme | null>(null)
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

// 限制输入长度为200字符，超过则截取更早输入的部分
watch(inputValue, (newVal) => {
  if (newVal.length > MAX_INPUT_LENGTH) {
    inputValue.value = newVal.slice(-MAX_INPUT_LENGTH)
  }
})

const updateTheme = () => {
  theme.value = mediaQuery.matches ? darkTheme : null
}

const connectWS = () => {
  if (ws.value) {
    ws.value.close()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const path = '/api/oscws'
  const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}://${host}${path}`

  ws.value = new WebSocket(wsUrl)
  ws.value.onopen = () => {
    currText.value = ''
    console.log('WebSocket connected')
  }
  ws.value.onerror = (error) => {
    currText.value = '[无法连接到后端程序, 请检查是否已启动]'
    console.error('WebSocket error:', error)
  }
  ws.value.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.data !== undefined) {
        currText.value = msg.data
      }
      if (msg.translation) {
        translationActive.value = msg.translation
      }
      if (msg.languages) {
        translationLanguages.value = msg.languages
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e)
    }
  }
}

const checkAndReconnect = () => {
  if (!ws.value || ws.value.readyState === WebSocket.CLOSED) {
    console.log('WebSocket disconnected, reconnecting...')
    connectWS()
  }
}

onMounted(() => {
  connectWS()
  reconnectTimer = setInterval(checkAndReconnect, 10000)
  updateTheme()
  mediaQuery.addEventListener('change', updateTheme)
  inputInstRef.value?.focus()
})

onUnmounted(() => {
  if (reconnectTimer !== null) {
    clearInterval(reconnectTimer)
  }
  ws.value?.close()
})

const undoClick = () => {
  if (history.value.length === 0) return
  const oldValue = history.value.pop()
  if (oldValue !== undefined) {
    inputValue.value = oldValue
  }
}

const clearClick = () => {
  clear()
  if (realTimeActive.value == false) {
    submitMsg('')
  }
}

const clear = () => {
  if (inputValue.value) {
    history.value.push(inputValue.value)
  }
  inputInstRef.value?.clear()
  inputInstRef.value?.focus()
}

const submit = () => {
  // if (!inputValue.value.trim()) return
  submitMsg(inputValue.value)
  clear()
}

const sendWSMessage = (data: Record<string, unknown>): boolean => {
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify(data))
    return true
  } else {
    console.error('WebSocket not connected')
    return false
  }
}

const submitMsg = (msg: string) => {
  // 截取文本处理
  // debugger
  const processedText = autoCutActive.value ? processText(msg, cutCount.value) : msg
  // const processedText = msg

  sendWSMessage({ data: processedText, realtime: realTimeActive.value })

  return processedText
  // currText.value = processedText
}

// 防抖定时器
let debounceTimer: ReturnType<typeof setTimeout> | null = null
// WebSocket 重连定时器
let reconnectTimer: ReturnType<typeof setInterval> | null = null

const handleCompositionStart = () => {
  isCompositing.value = true
}

const handleCompositionUpdate = (e: CompositionEvent) => {
  handleChange(inputValue.value + e.data)
}

const handleCompositionEnd = () => {
  isCompositing.value = false
  // compositionend 后触发一次 handleChange 把最终结果发出去
  handleChange(inputValue.value)
}

const handleChange = (value: string) => {
  if (!realTimeActive.value) {
    return
  }

  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }

  debounceTimer = setTimeout(() => {
    submitMsg(value)
    // const cutMsg = autoCutActive.value ? processText(value, cutCount.value) : value
    // currText.value = cutMsg
  }, 500)
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!realTimeActive.value) {
      submit()
    }
  }
}

const handleTranslationActiveChange = (active: boolean) => {
  sendWSMessage({ translation: active })
}

const handleLanguageChange = (strings: string[]) => {
  sendWSMessage({ languages: strings })
}


const copyClick = () => {
  if (navigator.clipboard && navigator.permissions) {
    console.log('Copying to clipboard...')
    navigator.clipboard.writeText(inputValue.value)
  } else {
    // 浏览器限制的情况下只能选中文本让用户复制了
    console.info('Clipboard API not supported')
    inputInstRef.value?.select()
  }
  sendWSMessage({ clipboard: inputValue.value })
}

function processText(input: string, cutCount: number = 2): string {
  // 匹配“句子 + 可能的结尾标点”，支持中英文
  // 使用非贪婪模式捕获句子内容
  const sentenceRegex = /[^。！？.!?\n]+[。！？.!?\n]?/g

  const matches = input.match(sentenceRegex)
  if (!matches || matches.length === 0) return input

  // 过滤掉空字符串（可能存在空格或换行）
  const sentences = matches.map((s) => s.trim()).filter((s) => s.length > 0)

  // 取最后两句
  const lastTwo = sentences.slice(-cutCount)

  const result = lastTwo.map((sentence) => {
    // 如果以句号结尾（中英文），去掉
    if (/[。.]\s*$/.test(sentence)) {
      return sentence.replace(/[。.]\s*$/, '')
    }

    // 问号、叹号保留
    return sentence
  })

  return result.join('\n')
}
</script>

<template>
  <main>
    <n-config-provider :theme="theme">
      <n-grid x-gap="12" y-gap="12" cols="1" responsive="screen">
        <n-grid-item>
          <n-card title="文本输入">
            <n-input ref="inputInstRef" v-model:value="inputValue" type="textarea" placeholder="请输入文本..." :input-props="{
              onCompositionstart: handleCompositionStart,
              onCompositionupdate: handleCompositionUpdate,
              onCompositionend: handleCompositionEnd,
            }" @input="handleChange" @keydown="handleKeydown" :autosize="{ minRows: 5, maxRows: 10 }" />
            <n-scrollbar x-scrollable trigger="none" style="margin-top: 1em">
              <n-form inline label-placement="left" label-width="auto" require-mark-placement="right-hanging">
                <n-form-item label="实时输入" style="padding-right: 10px">
                  <n-switch v-model:value="realTimeActive" />
                </n-form-item>
                <n-form-item label="翻译" style="padding-right: 40px">
                  <n-switch v-model:value="translationActive" @update:value="handleTranslationActiveChange" />
                </n-form-item>
                <n-form-item label="自动截取" style="padding-right: 40px">
                  <n-switch v-model:value="autoCutActive" />
                </n-form-item>
              </n-form>
            </n-scrollbar>
            <n-form label-placement="left" label-width="auto">
              <n-form-item label="翻译语言" v-show="translationActive">
                <n-dynamic-tags v-model:value="translationLanguages" :max="3" @change="handleLanguageChange" />
              </n-form-item>
              <n-form-item label="截取句数" v-show="autoCutActive" style="padding-right: 100px">
                <n-input-number v-model:value="cutCount" :min="1" size="small" style="flex-shrink: 0; width: 80px" />
              </n-form-item>
            </n-form>

            <n-space justify="space-between">
              <n-space>
                <n-button @click="undoClick">撤销</n-button>
                <n-button @click="clearClick">清除</n-button>
                <n-button @click="copyClick">复制</n-button>
              </n-space>
              <n-space justify="end">
                <n-button type="primary" @click="submit" :disabled="realTimeActive">提交</n-button></n-space>
            </n-space>
          </n-card>
          <div style="margin-top: 1em">
            <n-card><n-log :log="currText" trim :rows="10"></n-log></n-card>
          </div>
        </n-grid-item>
      </n-grid>
    </n-config-provider>
  </main>
</template>

<style scoped>
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 12px 12px;
}
</style>
