<script setup lang="ts">
import { darkTheme, NConfigProvider, NMessageProvider, NTabs, NTab } from 'naive-ui'
import type { GlobalTheme } from 'naive-ui'
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const theme = ref<GlobalTheme | null>(null)
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

const updateTheme = () => {
  theme.value = mediaQuery.matches ? darkTheme : null
}

onMounted(() => {
  updateTheme()
  mediaQuery.addEventListener('change', updateTheme)
})

const tabValue = ref(route.path)

const handleTabUpdate = (value: string) => {
  tabValue.value = value
  router.push(value)
}
</script>

<template>
  <n-config-provider :theme="theme">
    <n-message-provider placement="bottom">
      <div class="app-shell">
        <n-tabs
          :value="route.path"
          type="line"
          justify-content="space-evenly"
          @update:value="handleTabUpdate"
        >
          <n-tab name="/" tab="文本输入" />
          <n-tab name="/connect" tab="访问" />
          <n-tab name="/config" tab="配置" />
        </n-tabs>
        <router-view />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.app-shell {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 12px;
}
</style>
