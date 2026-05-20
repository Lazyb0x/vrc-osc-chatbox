<script setup lang="ts">
import { NForm, NFormItem, NInput, NInputNumber, NButton, NCard, useMessage } from 'naive-ui'
import { ref, onMounted } from 'vue'
import { getConfig, saveConfig, type ConfigData } from '@/api'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)

const defaultConfig = (): ConfigData => ({
  base: { logging_level: 'INFO', host: '0.0.0.0', port: 8000, osc_host: '127.0.0.1', osc_port: 9000 },
  openai: { model: '', api_base: '', api_key: null, prompt: null, thinking: null },
  translate: { enable: false, languages: [], tools: null },
})

const config = ref<ConfigData>(defaultConfig())

onMounted(async () => {
  loading.value = true
  try {
    config.value = await getConfig()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载配置失败')
  } finally {
    loading.value = false
  }
})

const handleSave = async () => {
  saving.value = true
  try {
    await saveConfig(config.value)
    message.success('保存成功')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main>
    <n-card>
      <n-form v-if="!loading" :model="config" autocomplete="off">
        <n-form-item label="OSC IP" path="base.osc_host">
          <p class="desc">OSC 目标 IP 地址，通常是 127.0.0.1</p>
          <n-input v-model:value="config.base.osc_host" placeholder="127.0.0.1" />
        </n-form-item>

        <n-form-item label="OSC 端口" path="base.osc_port">
          <p class="desc">OSC 目标端口，VRChat 默认 9000</p>
          <n-input-number v-model:value="config.base.osc_port" placeholder="9000" :min="1" :max="65535" />
        </n-form-item>

        <n-form-item label="模型名称" path="openai.model">
          <p class="desc">翻译使用的 AI 模型，如 gpt-4o</p>
          <n-input v-model:value="config.openai.model" placeholder="gpt-4o" />
        </n-form-item>

        <n-form-item label="接口地址" path="openai.api_base">
          <p class="desc">翻译使用的 API 地址，OpenAI 格式</p>
          <n-input v-model:value="config.openai.api_base" placeholder="https://api.openai.com/v1" />
        </n-form-item>

        <n-form-item label="访问令牌" path="openai.api_key">
          <p class="desc">用于访问翻译服务。获取方式请参考对应服务的官方文档</p>
          <n-input v-model:value="config.openai.api_key" type="password" :input-props="{
            autocomplete: 'new-password', name: 'openai-access-token'
          }" show-password-on="click" placeholder="sk-..." />
        </n-form-item>

        <n-button strong secondary :loading="saving" @click="handleSave" block>
          保存
        </n-button>
      </n-form>
    </n-card>
  </main>
</template>

<style scoped>
main {
  max-width: 720px;
  margin: 0 auto;
  padding: 12px 0;
}

.desc {
  margin: 0 0 4px;
  font-size: 12px;
  color: #999;
}

:deep(.n-form-item-blank) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
</style>
