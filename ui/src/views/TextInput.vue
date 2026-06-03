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
  Mic,
  MicOff,
} from '@vicons/ionicons5'
import type { InputInst } from 'naive-ui'
import { ref, shallowRef, computed, onMounted, onActivated, onUnmounted, watch, nextTick } from 'vue'

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

// ===== ASR 语音识别状态 =====
const asrState = ref<'idle' | 'recording' | 'processing'>('idle')
const interimText = ref('')
let asrWS: WebSocket | null = null
let audioCtx: AudioContext | null = null
let mediaStream: MediaStream | null = null
let workletNode: AudioWorkletNode | null = null
let gainNode: GainNode | null = null
let mediaSourceNode: MediaStreamAudioSourceNode | null = null

const micTooltip = computed(() => {
  if (asrState.value === 'recording') return '停止录音'
  if (asrState.value === 'processing') return '处理中...'
  return '语音输入'
})

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
  cleanupAudioCapture()
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

// ========== ASR 语音识别 ==========

function connectASRWS(): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const ws = new WebSocket(`${protocol}://${host}/api/asr`)
  asrWS = ws
  return ws
}

async function startASRRecording() {
  try {
    // 1. 获取麦克风权限（不指定 sampleRate，让浏览器使用默认值）
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    // 2. 连接 ASR WebSocket
    asrState.value = 'recording'
    const ws = connectASRWS()

    ws.onopen = async () => {
      // 3. 创建 AudioContext（不指定 sampleRate，与浏览器默认一致）
      audioCtx = new AudioContext()
      mediaSourceNode = audioCtx.createMediaStreamSource(mediaStream!)

      // 加载 AudioWorklet 模块并创建 processor（替代已废弃的 ScriptProcessorNode）
      await audioCtx.audioWorklet.addModule('/asr-worklet.js')
      workletNode = new AudioWorkletNode(audioCtx, 'asr-processor')
      workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (ws.readyState !== WebSocket.OPEN) return
        ws.send(event.data)
      }

      // 为了防止 Chromium 浏览器暂停无输出的音频图，
      // 将 worklet 输出连接到 muted GainNode → destination
      gainNode = audioCtx.createGain()
      gainNode.gain.value = 0

      mediaSourceNode.connect(workletNode)
      workletNode.connect(gainNode)
      gainNode.connect(audioCtx.destination)
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'interim') {
          interimText.value = msg.text
        } else if (msg.type === 'final') {
          interimText.value = ''
          // 去掉末尾的 。或 .
          const text = msg.text.replace(/[。.]$/, '')
          inputValue.value = text
          asrState.value = 'idle'
          cleanupAudioCapture()
        } else if (msg.type === 'error') {
          console.error('ASR error:', msg.text)
          interimText.value = `[语音识别错误: ${msg.text}]`
          asrState.value = 'idle'
          cleanupAudioCapture()
        }
      } catch (e) {
        console.error('Failed to parse ASR message:', e)
      }
    }

    ws.onerror = () => {
      interimText.value = '[ASR 连接失败]'
      asrState.value = 'idle'
      cleanupAudioCapture()
    }

    ws.onclose = () => {
      if (asrState.value === 'recording' || asrState.value === 'processing') {
        asrState.value = 'idle'
        interimText.value = ''
        cleanupAudioCapture()
      }
    }
  } catch (err) {
    console.error('Mic access denied:', err)
    asrState.value = 'idle'
    interimText.value = '[麦克风访问被拒绝]'
  }
}

function stopASRRecording() {
  asrState.value = 'processing'

  // 停止音频采集（不再发送 PCM 数据），但保留 WebSocket 等待 final 结果
  stopAudioTracks()

  // 发送 stop 命令
  if (asrWS && asrWS.readyState === WebSocket.OPEN) {
    asrWS.send(JSON.stringify({ action: 'stop' }))
    // 超时保护：5 秒后强制重置状态
    setTimeout(() => {
      if (asrState.value === 'processing') {
        asrState.value = 'idle'
        interimText.value = ''
        cleanupASRWS()
      }
    }, 5000)
  } else {
    cleanupASRWS()
    asrState.value = 'idle'
  }
}

function stopAudioTracks() {
  // 1. 先停止麦克风 Track，立即释放系统硬件（麦克风指示灯消失）
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
  }
  // 2. 断开音频图节点
  if (workletNode) {
    workletNode.port.onmessage = null
    workletNode.disconnect()
    workletNode = null
  }
  if (gainNode) {
    gainNode.disconnect()
    gainNode = null
  }
  if (mediaSourceNode) {
    mediaSourceNode.disconnect()
    mediaSourceNode = null
  }
  // 3. 最后关闭 AudioContext（异步，但硬件已释放，不影响）
  if (audioCtx) {
    audioCtx.close()
    audioCtx = null
  }
}

function cleanupASRWS() {
  if (asrWS) {
    asrWS.onclose = null
    asrWS.onerror = null
    asrWS.onmessage = null
    if (asrWS.readyState === WebSocket.OPEN || asrWS.readyState === WebSocket.CONNECTING) {
      asrWS.close()
    }
    asrWS = null
  }
}

function cleanupAudioCapture() {
  stopAudioTracks()
  cleanupASRWS()
}

function toggleMic() {
  if (asrState.value === 'idle') {
    startASRRecording()
  } else {
    stopASRRecording()
  }
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

          <div class="action-bar">
            <n-space class="action-left">
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
            <n-space class="action-right">
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-button :type="asrState === 'recording' ? 'error' : 'default'" :loading="asrState === 'processing'"
                    :disabled="asrState === 'processing'" @click="toggleMic">
                    <n-icon>
                      <Mic v-if="asrState !== 'recording'" />
                      <MicOff v-else />
                    </n-icon>
                  </n-button>
                </template>
                <span>{{ micTooltip }}</span>
              </n-popover>
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
          </div>
          <!-- ASR 中间结果 -->
          <div v-if="interimText && asrState !== 'idle'" class="asr-interim">
            {{ interimText }}
          </div>
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

.asr-interim {
  margin-top: 0.5em;
  margin-bottom: 0;
  padding: 0.5em 0.75em;
  border-radius: 6px;
  background: rgba(128, 128, 128, 0.1);
  color: var(--n-text-color-3, #888);
  font-size: 0.9em;
  line-height: 1.4;
  min-height: 1.4em;
}

.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1em;
}

.action-right {
  margin-left: auto;
}
</style>
