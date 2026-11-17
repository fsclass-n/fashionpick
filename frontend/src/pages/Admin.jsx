import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCircleNotch, faDatabase, faPen, faPlay, faPlus, faRobot, faServer, faStore, faTrash, faUsers,
} from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { dateTime, pct, timeAgo } from '../lib/format'
import { useAuth } from '../context/AuthContext'
import { useRealtime, useRealtimeEvent } from '../context/RealtimeContext'
import { Badge, ErrorBox, Modal, PageHeader, Spinner, StatCard, Tabs, Toggle, useAsync } from '../components/ui'
import Plot from '../components/Plot'

const JOB_STATUS = { idle: ['muted', '대기'], running: ['warn', '실행 중'], success: ['success', '성공'], failed: ['danger', '실패'] }
const INTERVALS = [15, 30, 60, 180, 360, 720, 1440]
const intervalLabel = (m) => (m >= 60 ? `${m / 60}시간` : `${m}분`)

function RpaPanel() {
  const { toast } = useRealtime()
  const jobs = useAsync(() => api('/api/admin/rpa/jobs'))
  const sys = useAsync(() => api('/api/admin/system'))
  const stats = useAsync(() => api('/api/admin/rpa/stats'))
  const [filter, setFilter] = useState({ job: '', status: '' })
  const logs = useAsync(() => api(`/api/admin/rpa/logs?limit=100${filter.job ? `&job=${filter.job}` : ''}${filter.status ? `&status=${filter.status}` : ''}`), [filter.job, filter.status])
  useRealtimeEvent('rpa.job', () => { jobs.reload(); logs.reload(); stats.reload() })

  const labels = useMemo(() => Object.fromEntries((jobs.data || []).map((j) => [j.name, j.label])), [jobs.data])
  const chart = useMemo(() => {
    const s = stats.data || []
    const x = s.map((r) => labels[r.job] || r.job)
    return [
      { type: 'bar', name: '성공', x, y: s.map((r) => r.success), marker: { color: '#2f7d5b' } },
      { type: 'bar', name: '실패', x, y: s.map((r) => r.failed), marker: { color: '#b4302a' } },
    ]
  }, [stats.data, labels])
  const chartLayout = useMemo(() => ({ barmode: 'stack', margin: { l: 32, r: 8, t: 8, b: 40 } }), [])

  const patch = async (name, body) => {
    try {
      await api(`/api/admin/rpa/jobs/${name}`, { method: 'PATCH', body })
      jobs.reload()
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '설정 변경 실패', body: e.message })
    }
  }
  const run = async (name) => {
    try {
      await api(`/api/admin/rpa/jobs/${name}/run`, { method: 'POST' })
      jobs.setData(jobs.data.map((j) => (j.name === name ? { ...j, running: true, last_status: 'running' } : j)))
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '실행 실패', body: e.message })
    }
  }

  return (
    <div className="space-y-6">
      {sys.data && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="RPA 모드" value={sys.data.rpa_mode.toUpperCase()} sub={sys.data.rpa_mode === 'demo' ? '샘플 데이터로 동작' : '실제 사이트 수집'} icon={faRobot} tone="accent" />
          <StatCard label="스케줄러" value={sys.data.scheduler_enabled ? 'ON' : 'OFF'} sub={`자동 발송 ${sys.data.auto_send_purchase_order ? 'ON' : 'OFF'}`} icon={faServer} />
          <StatCard label="Database" value={sys.data.database === 'sqlite' ? 'SQLite' : 'TiDB'} sub={`SMTP ${sys.data.smtp_configured ? '설정됨' : '미설정'}`} icon={faDatabase} />
          <StatCard label="실시간 접속" value={sys.data.ws_clients} sub={`데이터랩 ${sys.data.naver_datalab_configured ? '연동' : '미연동'} · 수집 대상 ${sys.data.trend_targets + sys.data.wholesale_targets}곳`} icon={faUsers} />
        </div>
      )}

      <ErrorBox error={jobs.error} />
      <div className="grid gap-4 lg:grid-cols-3">
        {(jobs.data || []).map((j) => {
          const [tone, label] = JOB_STATUS[j.running ? 'running' : j.last_status] || JOB_STATUS.idle
          return (
            <article key={j.name} className="card flex flex-col gap-4 p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="eyebrow">{j.name}</p>
                  <h3 className="mt-1 text-xl">{j.label}</h3>
                </div>
                <Badge tone={tone}>{j.running && <FontAwesomeIcon icon={faCircleNotch} spin />}{label}</Badge>
              </div>
              <p className="text-xs text-muted">마지막 실행 {j.last_run_at ? `${dateTime(j.last_run_at)} (${timeAgo(j.last_run_at)})` : '없음'}</p>
              <div className="flex items-center justify-between gap-3">
                <label className="text-sm text-muted" htmlFor={`int-${j.name}`}>수집 주기</label>
                <select id={`int-${j.name}`} className="input w-32 py-2" value={j.interval_minutes} onChange={(e) => patch(j.name, { interval_minutes: Number(e.target.value) })}>
                  {[...new Set([...INTERVALS, j.interval_minutes])].sort((a, b) => a - b).map((m) => <option key={m} value={m}>{intervalLabel(m)}</option>)}
                </select>
              </div>
              <Toggle checked={j.enabled} onChange={(v) => patch(j.name, { enabled: v })} label="주기 실행" desc="스케줄러가 주기마다 자동 실행" />
              <button className="btn-primary mt-auto" disabled={j.running} onClick={() => run(j.name)}>
                <FontAwesomeIcon icon={j.running ? faCircleNotch : faPlay} spin={j.running} /> 지금 실행
              </button>
            </article>
          )
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <section className="card p-5">
          <h3 className="text-xl">실행 결과 통계</h3>
          <div className="mt-2 space-y-1 text-xs text-muted">
            {(stats.data || []).map((s) => <p key={s.job}>{labels[s.job] || s.job} · 성공률 {pct(s.success_rate)} · 처리 {s.items.toLocaleString()}건</p>)}
          </div>
          <Plot data={chart} layout={chartLayout} height={260} />
        </section>
        <section>
          <div className="mb-3 flex flex-wrap gap-2">
            <select className="input w-auto py-2" value={filter.job} onChange={(e) => setFilter((f) => ({ ...f, job: e.target.value }))}>
              <option value="">전체 작업</option>
              {(jobs.data || []).map((j) => <option key={j.name} value={j.name}>{j.label}</option>)}
            </select>
            <select className="input w-auto py-2" value={filter.status} onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value }))}>
              <option value="">전체 상태</option><option value="success">성공</option><option value="failed">실패</option><option value="running">실행 중</option>
            </select>
          </div>
          <div className="table-wrap max-h-[28rem] overflow-y-auto">
            <table>
              <thead className="sticky top-0 bg-surface"><tr><th>시작</th><th>작업</th><th>상태</th><th>트리거</th><th className="text-right">건수</th><th>소요</th><th>메시지</th></tr></thead>
              <tbody>
                {(logs.data || []).map((l) => {
                  const [tone, label] = JOB_STATUS[l.status] || JOB_STATUS.idle
                  const secs = l.finished_at ? ((new Date(l.finished_at) - new Date(l.started_at)) / 1000).toFixed(1) : '-'
                  return (
                    <tr key={l.id}>
                      <td className="text-muted">{dateTime(l.started_at)}</td>
                      <td>{labels[l.job_name] || l.job_name}</td>
                      <td><Badge tone={tone}>{label}</Badge></td>
                      <td className="text-muted">{l.triggered_by === 'manual' ? '수동' : '스케줄'}</td>
                      <td className="text-right">{l.items_count}</td>
                      <td className="text-muted">{secs}s</td>
                      <td className="max-w-80 truncate text-xs text-muted" title={l.message}>{l.message}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}

const EMPTY_SUPPLIER = { name: '', contact_name: '', phone: '', email: '', webhook_url: '', order_method: 'email', template: 'standard', address: '', memo: '' }

function SupplierPanel() {
  const { data, loading, error, reload } = useAsync(() => api('/api/suppliers'))
  const [edit, setEdit] = useState(null)
  const [err, setErr] = useState(null)
  const { toast } = useRealtime()

  const save = async (e) => {
    e.preventDefault()
    setErr(null)
    try {
      const { id, created_at: _c, ...body } = edit
      await api(id ? `/api/suppliers/${id}` : '/api/suppliers', { method: id ? 'PUT' : 'POST', body })
      setEdit(null)
      reload()
    } catch (e2) {
      setErr(e2)
    }
  }
  const remove = async (s) => {
    if (!window.confirm(`'${s.name}' 공급처를 삭제할까요?`)) return
    try {
      await api(`/api/suppliers/${s.id}`, { method: 'DELETE' })
      reload()
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '삭제 실패', body: e.message })
    }
  }
  const field = (k, label, props = {}) => (
    <div>
      <label className="label" htmlFor={`sup-${k}`}>{label}</label>
      <input id={`sup-${k}`} className="input" value={edit[k] ?? ''} onChange={(e) => setEdit((s) => ({ ...s, [k]: e.target.value }))} {...props} />
    </div>
  )

  return (
    <>
      <div className="mb-4 flex justify-end"><button className="btn-primary" onClick={() => setEdit({ ...EMPTY_SUPPLIER })}><FontAwesomeIcon icon={faPlus} />공급처 추가</button></div>
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>공급처</th><th>담당자</th><th>연락처</th><th>수신 방식</th><th>템플릿</th><th>이메일 / 웹훅</th><th></th></tr></thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td className="font-medium">{s.name}</td>
                  <td>{s.contact_name}</td>
                  <td className="text-muted">{s.phone}</td>
                  <td><Badge tone={s.order_method === 'manual' ? 'muted' : 'accent'}>{{ email: '이메일', webhook: '웹훅', manual: '수동' }[s.order_method]}</Badge></td>
                  <td className="text-muted">{s.template === 'simple' ? '간단형' : '표준형'}</td>
                  <td className="max-w-56 truncate text-muted">{s.order_method === 'webhook' ? s.webhook_url : s.email}</td>
                  <td className="text-right">
                    <button className="px-2 text-muted hover:text-fg" onClick={() => setEdit({ ...s })} aria-label="수정"><FontAwesomeIcon icon={faPen} /></button>
                    <button className="px-2 text-muted hover:text-danger" onClick={() => remove(s)} aria-label="삭제"><FontAwesomeIcon icon={faTrash} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? '공급처 수정' : '공급처 추가'}>
        {edit && (
          <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">{field('name', '공급처명', { required: true })}</div>
            {field('contact_name', '담당자')}
            {field('phone', '연락처')}
            <div>
              <label className="label" htmlFor="sup-method">발주서 수신 방식</label>
              <select id="sup-method" className="input" value={edit.order_method} onChange={(e) => setEdit((s) => ({ ...s, order_method: e.target.value }))}>
                <option value="email">이메일 (Excel·PDF 첨부)</option><option value="webhook">웹훅 (JSON)</option><option value="manual">수동 (전화·팩스)</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="sup-template">발주 템플릿</label>
              <select id="sup-template" className="input" value={edit.template} onChange={(e) => setEdit((s) => ({ ...s, template: e.target.value }))}>
                <option value="standard">표준형 (주문번호 포함)</option><option value="simple">간단형</option>
              </select>
            </div>
            <div className="sm:col-span-2">{field('email', '이메일', { type: 'email' })}</div>
            <div className="sm:col-span-2">{field('webhook_url', '웹훅 URL', { type: 'url', placeholder: 'https://' })}</div>
            <div className="sm:col-span-2">{field('address', '주소')}</div>
            <div className="sm:col-span-2"><ErrorBox error={err} /></div>
            <div className="grid grid-cols-2 gap-2 sm:col-span-2">
              <button type="button" className="btn-ghost" onClick={() => setEdit(null)}>취소</button>
              <button className="btn-accent">저장</button>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}

function UserPanel() {
  const { user: me } = useAuth()
  const { toast } = useRealtime()
  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const { data, loading, error, reload, setData } = useAsync(() => api(`/api/admin/users${query ? `?q=${encodeURIComponent(query)}` : ''}`), [query])
  useRealtimeEvent('admin.user_role', reload)

  const change = async (u, role) => {
    try {
      const updated = await api(`/api/admin/users/${u.id}/role`, { method: 'PATCH', body: { role } })
      setData(data.map((x) => (x.id === u.id ? updated : x)))
      toast({ tone: 'success', icon: 'user', title: '권한 변경 완료', body: `${u.name} → ${role === 'admin' ? '관리자' : '일반 사용자'}` })
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '권한 변경 실패', body: e.message })
    }
  }

  return (
    <>
      <form className="mb-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(q.trim()) }}>
        <input className="input max-w-sm rounded-full" placeholder="이름·이메일 검색" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-ghost">검색</button>
      </form>
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>이름</th><th>이메일</th><th>가입 경로</th><th>가입일</th><th>최근 로그인</th><th>권한</th></tr></thead>
            <tbody>
              {data.map((u) => (
                <tr key={u.id}>
                  <td className="font-medium">{u.name} {u.id === me.id && <Badge>나</Badge>}</td>
                  <td className="text-muted">{u.email}</td>
                  <td><Badge>{u.provider}</Badge></td>
                  <td className="text-muted">{dateTime(u.created_at)}</td>
                  <td className="text-muted">{timeAgo(u.last_login_at)}</td>
                  <td>
                    <div className="inline-flex rounded-full border border-line p-0.5 text-xs">
                      {[['user', '일반 사용자'], ['admin', '관리자']].map(([r, l]) => (
                        <button key={r} disabled={u.id === me.id && r === 'user'} onClick={() => u.role !== r && change(u, r)}
                          className={`rounded-full px-3 py-1 transition disabled:opacity-40 ${u.role === r ? (r === 'admin' ? 'bg-accent text-white' : 'bg-fg text-bg') : 'text-muted hover:text-fg'}`}>
                          {l}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export default function Admin() {
  const [tab, setTab] = useState('rpa')
  return (
    <>
      <PageHeader eyebrow="Administrator" title={<>Control <span className="italic">room</span></>}
        desc="Playwright 기반 RPA 작업 상태와 로그를 모니터링하고, 공급처와 회원 권한을 관리합니다." />
      <Tabs value={tab} onChange={setTab} tabs={[
        { value: 'rpa', label: 'RPA 작업', icon: faRobot }, { value: 'suppliers', label: '공급처', icon: faStore }, { value: 'users', label: '회원 권한', icon: faUsers },
      ]} />
      {tab === 'rpa' && <RpaPanel />}
      {tab === 'suppliers' && <SupplierPanel />}
      {tab === 'users' && <UserPanel />}
    </>
  )
}
