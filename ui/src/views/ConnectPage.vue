<script setup lang="ts">
import { NSelect, NInput, NButton, NSpace, NCard, NQrCode } from 'naive-ui'
import { ref, onMounted } from 'vue'
import { getIpInfo, type IpInfoData } from '@/api'

const loading = ref(false)
const error = ref('')
const ipData = ref<IpInfoData | null>(null)
const selectedAddress = ref('')
let port: number | null = null

interface SelectOption {
  label: string
  value: string
}

const options = ref<SelectOption[]>([])
const selectValue = ref('')
const canCopy = ref(false)

onMounted(async () => {
  canCopy.value = !!(navigator.clipboard && navigator.permissions)
  loading.value = true
  error.value = ''
  try {
    ipData.value = await getIpInfo()
    port = ipData.value.port
    options.value = ipData.value.ipInfos.map((info) => ({
      label: info.networkName,
      value: info.ip,
    }))
    if (options.value.length > 0) {
      const value = options.value[0]!.value
      selectedAddress.value = `http://${value}:${port}`
      selectValue.value = options.value[0]!.value
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '获取网络信息失败'
  } finally {
    loading.value = false
  }
})

const handleSelect = (value: string) => {
  selectedAddress.value = `http://${value}:${port}`
}

const copyAddress = async () => {
  if (!selectedAddress.value) return
  await navigator.clipboard.writeText(selectedAddress.value)
}
</script>

<template>
  <main>
    <!-- <n-space vertical> -->
    <n-card>
      <p v-if="!loading && error" style="color: red">{{ error }}</p>
      <p v-if="!loading && options.length === 0">未找到可用网络</p>

      <template v-if="!loading && !error && options.length > 0">
        <n-space vertical align="center">
          <p>在同一局域网内打开此页面</p>

          <n-qr-code :value="selectedAddress" :maxlength="60" type="text" :size="200" />

          <n-space vertical style="margin-top: 1em; width: 16.5em;">
            <n-select :options="options" @update:value="handleSelect" placeholder="网络" v-model:value="selectValue" />
            <n-input v-if="selectedAddress" :value="selectedAddress" readonly>
              <template #suffix>
                <n-button v-if="canCopy" text type="primary" @click="copyAddress">复制</n-button>
              </template>
            </n-input>
          </n-space>

        </n-space>

      </template>
    </n-card>
    <!-- </n-space> -->
  </main>
</template>

<style scoped>
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 12px 0px;
}
</style>
