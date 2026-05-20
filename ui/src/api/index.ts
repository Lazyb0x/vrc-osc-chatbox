export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

export interface IpInfo {
  ip: string
  networkName: string
  networkPrefix: number | null
  adapterName: string
}

export interface IpInfoData {
  port: number
  ipInfos: IpInfo[]
}

async function apiFetch<T>(endpoint: string): Promise<T> {
  const url = `${endpoint}`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  }
  const json: ApiResponse<T> = await res.json()
  if (json.code !== 0) {
    throw new Error(json.msg || 'Unknown error')
  }
  return json.data
}

export function getIpInfo(): Promise<IpInfoData> {
  return apiFetch<IpInfoData>('/api/ip-info')
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type ConfigData = Record<string, any>

export function getConfig(): Promise<ConfigData> {
  return apiFetch<ConfigData>('/api/config')
}

export async function saveConfig(data: ConfigData): Promise<void> {
  const res = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`)
  }
}
