import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { WS_URL } from '../lib/api'
import { won } from '../lib/format'
import { useAuth } from './AuthContext'

const RealtimeContext = createContext(null)

const DEFAULT_PREFS = { order: true, po: true, trend: true, rpa: true, popup: true, browser: false, sound: false }
const PREF_KEY = 'fp_notify_prefs'
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36)

function loadPrefs() {
  try {
    return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREF_KEY) || '{}') }
  } catch {
    return DEFAULT_PREFS
  }
}

/** 서버 이벤트 -> 토스트 메시지 변환 */
function describe(event, d) {
  switch (event) {
    case 'order.created':
      return { pref: 'order', tone: 'accent', icon: 'bag', title: '신규 주문 접수', body: `${d.order_no} · ${d.customer_name} · ${won(d.total_amount)}`, link: '/orders', popup: true }
    case 'po.created':
      return { pref: 'po', tone: 'info', icon: 'file', title: '발주서 자동 생성', body: `${d.supplier_name} · ${d.po_no} · ${won(d.total_amount)}`, link: '/orders?tab=po' }
    case 'po.updated':
      return { pref: 'po', tone: 'success', icon: 'send', title: '발주 상태 변경', body: `${d.supplier_name} · ${d.po_no} → ${{ pending: '대기', sent: '발송 완료', received: '입고 확인' }[d.status]}`, link: '/orders?tab=po' }
    case 'po.failed':
      return { pref: 'po', tone: 'danger', icon: 'warn', title: '발주서 발송 실패', body: `${d.po_no} · ${d.error}`, link: '/orders?tab=po' }
    case 'trend.surge':
      return { pref: 'trend', tone: 'accent', icon: 'fire', title: '급상승 트렌드 키워드', body: `#${d.keyword} (${d.category}) · ${d.rank}위 · +${Math.round(d.growth * 100)}%`, link: '/trends' }
    case 'rpa.job':
      if (d.status === 'running') return null
      return { pref: 'rpa', tone: d.status === 'success' ? 'success' : 'danger', icon: 'robot', title: `RPA ${d.status === 'success' ? '완료' : '실패'} · ${d.label}`, body: d.message, link: '/admin' }
    case 'user.role':
      return { pref: null, tone: 'info', icon: 'user', title: '권한이 변경되었습니다', body: d.role === 'admin' ? '관리자 권한이 부여되었습니다.' : '일반 사용자로 변경되었습니다.' }
    default:
      return null
  }
}

function beep() {
  try {
    const ctx = new AudioContext()
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.frequency.value = 880
    g.gain.setValueAtTime(0.08, ctx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35)
    o.connect(g).connect(ctx.destination)
    o.start()
    o.stop(ctx.currentTime + 0.35)
  } catch {
    /* 오디오 미지원 환경 무시 */
  }
}

export function RealtimeProvider({ children }) {
  const { token, refresh } = useAuth()
  const [status, setStatus] = useState('offline')
  const [toasts, setToasts] = useState([])
  const [popup, setPopup] = useState(null)
  const [feed, setFeed] = useState([])
  const [prefs, setPrefs] = useState(loadPrefs)
  const listeners = useRef(new Set())
  const prefsRef = useRef(prefs)
  prefsRef.current = prefs

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), [])

  const toast = useCallback(
    (t) => {
      const id = uid()
      setToasts((list) => [...list.slice(-4), { id, tone: 'info', ...t }])
      setTimeout(() => dismiss(id), t.duration || 5000)
    },
    [dismiss],
  )

  const subscribe = useCallback((fn) => {
    listeners.current.add(fn)
    return () => listeners.current.delete(fn)
  }, [])

  const updatePrefs = useCallback((patch) => {
    setPrefs((p) => {
      const next = { ...p, ...patch }
      localStorage.setItem(PREF_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  useEffect(() => {
    if (!token) return undefined
    let ws
    let retry = 0
    let closed = false
    let pingTimer
    let retryTimer

    const connect = () => {
      setStatus('connecting')
      ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`)
      ws.onopen = () => {
        retry = 0
        setStatus('online')
        pingTimer = setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000)
      }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.event === 'hello' || msg.event === 'pong') return
        listeners.current.forEach((fn) => fn(msg))
        if (msg.event === 'user.role') refresh()
        const info = describe(msg.event, msg.data)
        if (!info) return
        setFeed((f) => [{ ...info, id: uid(), at: msg.at }, ...f].slice(0, 30))
        const p = prefsRef.current
        if (info.pref && !p[info.pref]) return
        toast(info)
        if (info.popup && p.popup) setPopup({ ...info, data: msg.data })
        if (p.sound) beep()
        if (p.browser && 'Notification' in window && Notification.permission === 'granted' && document.hidden) {
          new Notification(info.title, { body: info.body, icon: '/favicon.svg' })
        }
      }
      ws.onclose = (e) => {
        clearInterval(pingTimer)
        setStatus('offline')
        if (closed || e.code === 4401) return
        retryTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++))
      }
    }
    connect()
    return () => {
      closed = true
      clearInterval(pingTimer)
      clearTimeout(retryTimer)
      ws?.close()
    }
  }, [token, toast, refresh])

  return (
    <RealtimeContext.Provider value={{ status, toasts, dismiss, toast, popup, closePopup: () => setPopup(null), feed, prefs, updatePrefs, subscribe }}>
      {children}
    </RealtimeContext.Provider>
  )
}

export const useRealtime = () => useContext(RealtimeContext)

/** 특정 이벤트 발생 시 콜백 (데이터 자동 새로고침 용도) */
export function useRealtimeEvent(events, handler) {
  const { subscribe } = useRealtime()
  const ref = useRef(handler)
  ref.current = handler
  const key = [].concat(events).join(',')
  useEffect(() => subscribe((msg) => key.split(',').includes(msg.event) && ref.current(msg)), [subscribe, key])
}
