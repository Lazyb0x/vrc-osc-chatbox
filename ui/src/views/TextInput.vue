<script setup lang="ts">
import {
  NButton,
  NCard,
  NDynamicTags,
  NSpace,
  NInput,
  NGrid,
  NGridItem,
  NInputNumber,
  NSwitch,
  NForm,
  NFormItem,
  NScrollbar,
  NLog,
  NIcon,
  NPopover,
} from 'naive-ui'
import {
  ArrowUndoOutline,
  CopyOutline,
  LockClosed,
  LockOpenOutline,
  TrashOutline,
  Send,
} from '@vicons/ionicons5'
import type { InputInst } from 'naive-ui'
import { ref, shallowRef, onMounted, onActivated, onUnmounted, watch } from 'vue'

const placeholders = [
  '请输入文本…',
  '是啊，吃什么…',
  '干嘛…',
  '今晚的月色…',
  '难道说…',
  '那个…',
  '呐…',
  '黄瓜…',
  '对吗…',
  '不对…',
  'a',
  '然而，然而…',
]

const MAX_INPUT_LENGTH = 200
const PLACEHOLDER_WEIGHT = 0.5
const REAL_TIME_INTERVAL = 1000
const PIN_INTERVAL = 5000


const getPlaceholderIndex = () => {
  const r = Math.random()
  return r < PLACEHOLDER_WEIGHT ? 0 : 1 +
    Math.floor(((r - PLACEHOLDER_WEIGHT) / (1 - PLACEHOLDER_WEIGHT)) * (placeholders.length - 1))
}
const placeholder = ref(placeholders[getPlaceholderIndex()])

const inputValue = ref('')
const inputInstRef = ref<InputInst | null>(null)
const history = ref<string[]>([])
const ws = ref<WebSocket | null>(null)
const realTimeActive = ref(false)
const autoCutActive = ref(false)
const translationActive = ref(false)
const pinned = ref(false)
const cutCount = ref(2)
const currText = shallowRef('')
const isCompositing = ref(false)
const compositionValue = ref('')
const translationLanguages = ref(['en'])

const lastSentValue = ref('')
let lastTypingSentTime = 0

watch(inputValue, (newVal) => {
  if (newVal.length > MAX_INPUT_LENGTH) {
    inputValue.value = newVal.slice(-MAX_INPUT_LENGTH)
  }
})

const connectWS = () => {
  if (ws.value) {
    ws.value.close()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const path = '/api/oscws'
  const wsUrl = `${protocol}://${host}${path}`

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
  inputInstRef.value?.focus()
})

onActivated(() => {
  inputInstRef.value?.focus()
  placeholder.value = placeholders[getPlaceholderIndex()]
})

onUnmounted(() => {
  stopRealTimeInterval()
  stopPinnedInterval()
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
  submitMsg('')
}

const clear = () => {
  if (inputValue.value) {
    history.value.push(inputValue.value)
  }
  inputInstRef.value?.clear()
  inputInstRef.value?.focus()
}

const submit = () => {
  submitMsg(inputValue.value)
  lastSentValue.value = ''
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
  const processedText = autoCutActive.value ? processText(msg, cutCount.value) : msg

  const msgObj: Record<string, unknown> = {
    data: processedText,
    realtime: realTimeActive.value
  }

  // 非实时输入时发送 关闭输入中状态
  if (!realTimeActive.value) {
    msgObj.typing = false
  }
  sendWSMessage(msgObj)

  return processedText
}

const submitTyping = (typing: boolean = true) => {
  sendWSMessage({ typing: typing })
}

let realTimeTimer: ReturnType<typeof setInterval> | null = null
let reconnectTimer: ReturnType<typeof setInterval> | null = null
let pinnedTimer: ReturnType<typeof setInterval> | null = null

const startRealTimeInterval = () => {
  stopRealTimeInterval()
  realTimeTimer = setInterval(() => {
    const currentText = inputValue.value + (isCompositing.value ? compositionValue.value : '')
    if (currentText === lastSentValue.value) return
    submitMsg(currentText)
    lastSentValue.value = currentText
  }, REAL_TIME_INTERVAL)
}

const stopRealTimeInterval = () => {
  if (realTimeTimer !== null) {
    clearInterval(realTimeTimer)
    realTimeTimer = null
  }
}

const startPinnedInterval = () => {
  stopPinnedInterval()
  submitMsg(inputValue.value)
  pinnedTimer = setInterval(() => {
    submitMsg(inputValue.value)
  }, PIN_INTERVAL)
}

const stopPinnedInterval = () => {
  if (pinnedTimer !== null) {
    clearInterval(pinnedTimer)
    pinnedTimer = null
  }
}

watch(realTimeActive, (active) => {
  if (active) {
    lastSentValue.value = inputValue.value
    submitMsg(inputValue.value)
    startRealTimeInterval()
  } else {
    stopRealTimeInterval()
    lastSentValue.value = ''
  }
})

watch(pinned, (active) => {
  if (active) {
    startPinnedInterval()
  } else {
    stopPinnedInterval()
  }
})

const handleCompositionStart = () => {
  isCompositing.value = true
}

const handleCompositionUpdate = (e: CompositionEvent) => {
  compositionValue.value = e.data
}

const handleCompositionEnd = () => {
  isCompositing.value = false
  compositionValue.value = ''
}

const handleChange = (value: string) => {
  if (realTimeActive.value) {
    // 实时模式：由 interval 轮询处理发送
    return
  }
  // 非实时模式：节流发送输入中状态，最多每2秒一次
  if (value.length > 0) {
    const now = Date.now()
    if (now - lastTypingSentTime >= 2000) {
      submitTyping(true)
      lastTypingSentTime = now
    }
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    e.preventDefault()
    if (!realTimeActive.value) {
      submit()
    }
  }
}

const handleTranslationActiveChange = (active: boolean) => {
  if (active) {
    pinned.value = false
  }
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
    console.info('Clipboard API not supported')
    inputInstRef.value?.select()
  }
  sendWSMessage({ clipboard: inputValue.value })
}

function processText(input: string, cutCount: number = 2): string {
  const sentenceRegex = /[^。！？.!?\n]+[。！？.!?\n]?/g

  const matches = input.match(sentenceRegex)
  if (!matches || matches.length === 0) return input

  const sentences = matches.map((s) => s.trim()).filter((s) => s.length > 0)

  const lastTwo = sentences.slice(-cutCount)

  const result = lastTwo.map((sentence) => {
    if (/[。.]\s*$/.test(sentence)) {
      return sentence.replace(/[。.]\s*$/, '')
    }

    return sentence
  })

  return result.join('\n')
}
</script>

<template>
  <main>
    <n-grid x-gap="12" y-gap="12" cols="1" responsive="screen">
      <n-grid-item>
        <n-card>
          <n-input ref="inputInstRef" v-model:value="inputValue" type="textarea" :placeholder="placeholder"
            :input-props="{
              onCompositionstart: handleCompositionStart,
              onCompositionupdate: handleCompositionUpdate,
              onCompositionend: handleCompositionEnd,
            }" @input="handleChange" @keydown="handleKeydown" :autosize="{ minRows: 5, maxRows: 10 }" />
          <n-scrollbar x-scrollable trigger="none" style="margin-top: 1em">
            <n-form inline label-placement="left" label-width="auto" require-mark-placement="right-hanging">
              <n-form-item label="实时输入">
                <n-switch v-model:value="realTimeActive" />
              </n-form-item>
              <n-form-item label="自动截取" v-show="realTimeActive" style="padding-left: 40px;padding-right: 10px">
                <n-switch v-model:value="autoCutActive" />
              </n-form-item>
              <n-form-item label="翻译" style="padding-right: 40px">
                <n-switch v-model:value="translationActive" @update:value="handleTranslationActiveChange" />
              </n-form-item>
            </n-form>
          </n-scrollbar>
          <n-form label-placement="left" label-width="auto">
            <n-form-item label="翻译语言" v-show="translationActive">
              <n-dynamic-tags v-model:value="translationLanguages" :closable="translationLanguages.length > 1" :max="3"
                @update:value="handleLanguageChange" />
            </n-form-item>
            <n-form-item label="截取句数" v-show="autoCutActive" style="padding-right: 100px">
              <n-input-number v-model:value="cutCount" :min="1" size="small" style="flex-shrink: 0; width: 80px" />
            </n-form-item>
          </n-form>

          <n-space justify="space-between">
            <n-space>
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button @click="undoClick">
                    <n-icon>
                      <ArrowUndoOutline />
                    </n-icon>
                  </n-button>
                </template>
                <span>撤销</span>
              </n-popover>
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button @click="clearClick">
                    <n-icon>
                      <TrashOutline />
                    </n-icon>
                  </n-button>
                </template>
                <span>清除</span>
              </n-popover>
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button @click="copyClick">
                    <n-icon size="13">
                      <CopyOutline />
                    </n-icon>
                  </n-button>
                </template>
                <span>复制</span>
              </n-popover>
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button :type="pinned ? 'primary' : 'default'" @click="pinned = !pinned"
                    :disabled="translationActive">
                    <n-icon>
                      <LockClosed v-if="pinned" />
                      <LockOpenOutline v-else />
                    </n-icon>
                  </n-button>
                </template>
                <span>{{ pinned ? '已固定' : '固定' }}</span>
              </n-popover>
            </n-space>
            <n-space justify="end">
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button type="primary" @click="submit" :disabled="realTimeActive">
                    <n-icon>
                      <Send />
                    </n-icon>
                  </n-button>
                </template>
                <span>发送 (Ctrl + Enter)</span>
              </n-popover>
            </n-space>
          </n-space>
        </n-card>
        <div style="margin-top: 1em">
          <n-card><n-log :log="currText" trim :rows="10"></n-log></n-card>
        </div>
      </n-grid-item>
    </n-grid>
  </main>
</template>

<style scoped>
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 12px 0px;
}
</style>
