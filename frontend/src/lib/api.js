// VITE_API_BASE_URL 미설정 시: 프로덕션 빌드는 Render API, 개발 서버는 로컬 API
const DEFAULT_API = import.meta.env.PROD ? 'https://fashionpick-api.onrender.com' : 'http://localhost:8000'
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API).replace(/\/$/, '')
export const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws'

const TOKEN_KEY = 'fp_token'
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function errorMessage(body, status) {
  if (!body) return `요청 실패 (${status})`
  if (typeof body.detail === 'string') return body.detail
  if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg?.replace(/^Value error, /, '')).join('\n')
  return `요청 실패 (${status})`
}

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const headers = {}
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let res
  try {
    res = await fetch(API_BASE + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(0, 'API 서버에 연결할 수 없습니다. (Render 무료 티어는 첫 요청 시 기동에 30초 이상 걸릴 수 있습니다)')
  }
  if (res.status === 401 && token) window.dispatchEvent(new Event('fp:unauthorized'))
  if (!res.ok) throw new ApiError(res.status, errorMessage(await res.json().catch(() => null), res.status))
  if (raw) return res
  return res.status === 204 ? null : res.json()
}

export async function download(path, fallbackName) {
  const res = await api(path, { raw: true })
  const cd = res.headers.get('Content-Disposition') || ''
  const m = cd.match(/filename\*=UTF-8''([^;]+)/)
  const name = m ? decodeURIComponent(m[1]) : fallbackName
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: name })
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export const mediaUrl = (url) => (!url ? '' : url.startsWith('/') ? API_BASE + url : url)

export const oauthUrl = (provider) =>
  `${API_BASE}/api/auth/oauth/${provider}/login?redirect=${encodeURIComponent(window.location.origin)}`
