import { useOsTheme } from 'naive-ui'
import { ref } from 'vue'

const osThemeRef = useOsTheme()
const currentTheme = ref(osThemeRef.value)

export { currentTheme }
