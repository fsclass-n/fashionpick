import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleNotch, faXmark, faBoxOpen } from '@fortawesome/free-solid-svg-icons'

const TONES = {
  muted: 'border-line text-muted',
  accent: 'border-accent/40 bg-accent/10 text-accent',
  success: 'border-success/40 bg-success/10 text-success',
  warn: 'border-warn/40 bg-warn/10 text-warn',
  danger: 'border-danger/40 bg-danger/10 text-danger',
  info: 'border-fg/20 bg-fg/5 text-fg',
}

export function Badge({ tone = 'muted', children, className = '' }) {
  return <span className={`chip font-medium ${TONES[tone] || TONES.muted} ${className}`}>{children}</span>
}

export function Spinner({ label = '불러오는 중' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted">
      <FontAwesomeIcon icon={faCircleNotch} spin /> {label}
    </div>
  )
}

export function Empty({ title = '데이터가 없습니다', desc, icon = faBoxOpen, action }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line px-6 py-14 text-center">
      <FontAwesomeIcon icon={icon} className="text-2xl text-muted" />
      <p className="font-medium">{title}</p>
      {desc && <p className="max-w-sm text-sm text-muted">{desc}</p>}
      {action}
    </div>
  )
}

export function ErrorBox({ error }) {
  if (!error) return null
  return <div className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm whitespace-pre-line text-danger">{String(error.message || error)}</div>
}

export function PageHeader({ eyebrow, title, desc, actions }) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
        <h1 className="text-3xl leading-tight md:text-5xl">{title}</h1>
        {desc && <p className="mt-3 max-w-2xl text-sm text-muted md:text-base">{desc}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function StatCard({ label, value, sub, icon, tone }) {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between">
        <span className="eyebrow">{label}</span>
        {icon && (
          <span className={`grid size-9 place-items-center rounded-full ${tone === 'accent' ? 'bg-accent text-white' : 'bg-surface-2'}`}>
            <FontAwesomeIcon icon={icon} className="text-sm" />
          </span>
        )}
      </div>
      <div className="font-display text-3xl md:text-4xl">{value}</div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-6 flex gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1 md:inline-flex">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={`shrink-0 rounded-full px-4 py-2 text-sm transition ${value === t.value ? 'bg-fg text-bg' : 'text-muted hover:text-fg'}`}
        >
          {t.icon && <FontAwesomeIcon icon={t.icon} className="mr-2" />}
          {t.label}
          {t.count != null && <span className="ml-2 opacity-60">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="animate-fade-in fixed inset-0 z-[70] flex items-end justify-center bg-black/50 backdrop-blur-sm md:items-center md:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className={`animate-toast-in max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-surface p-6 md:rounded-3xl ${wide ? 'md:max-w-4xl' : 'md:max-w-lg'}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <h2 className="text-2xl">{title}</h2>
          <button onClick={onClose} className="grid size-9 shrink-0 place-items-center rounded-full hover:bg-surface-2" aria-label="닫기">
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Toggle({ checked, onChange, label, desc }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-3">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        {desc && <span className="block text-xs text-muted">{desc}</span>}
      </span>
      <span className={`relative h-6 w-11 shrink-0 rounded-full transition ${checked ? 'bg-accent' : 'bg-line'}`}>
        <input type="checkbox" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
        <span className={`absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition ${checked ? 'translate-x-5' : ''}`} />
      </span>
    </label>
  )
}

/** 비동기 데이터 로딩 훅 */
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true }))
    fn()
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((error) => alive && setState({ data: null, error, loading: false }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { ...state, reload: () => setTick((t) => t + 1), setData: (data) => setState((s) => ({ ...s, data })) }
}
