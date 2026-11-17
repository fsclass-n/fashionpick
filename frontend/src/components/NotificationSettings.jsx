import { useState } from 'react'
import { useRealtime } from '../context/RealtimeContext'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import { Toggle } from './ui'

export default function NotificationSettings() {
  const { prefs, updatePrefs, status } = useRealtime()
  const { isAdmin } = useAuth()
  const { dark, toggle } = useTheme()
  const [perm, setPerm] = useState(() => ('Notification' in window ? Notification.permission : 'unsupported'))

  const setBrowser = async (on) => {
    if (on && perm !== 'granted' && 'Notification' in window) {
      const p = await Notification.requestPermission()
      setPerm(p)
      if (p !== 'granted') return
    }
    updatePrefs({ browser: on })
  }

  return (
    <>
      <p className="mb-5 text-[13px] text-muted">WebSocket 실시간 알림 수신 항목을 설정합니다. 설정은 이 브라우저에 저장됩니다.</p>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card divide-y divide-line px-6 py-2">
          <Toggle checked={prefs.order} onChange={(v) => updatePrefs({ order: v })} label="주문 알림" desc={isAdmin ? '신규 주문 접수 시 토스트 알림' : '내 주문 접수·발주·입고 상태 변경 알림'} />
          {isAdmin && <Toggle checked={prefs.popup} onChange={(v) => updatePrefs({ popup: v })} label="신규 주문 팝업 (관리자)" desc="주문 발생 시 화면 중앙 팝업 표시" />}
          {isAdmin && <Toggle checked={prefs.po} onChange={(v) => updatePrefs({ po: v })} label="발주서 생성·발송 알림 (관리자)" desc="발주서 자동 생성, 발송, 상태 변경, 실패" />}
          <Toggle checked={prefs.trend} onChange={(v) => updatePrefs({ trend: v })} label="급상승 키워드 알림" desc="트렌드 수집 결과 급상승 키워드 감지 시" />
          {isAdmin && <Toggle checked={prefs.rpa} onChange={(v) => updatePrefs({ rpa: v })} label="RPA 작업 결과 알림 (관리자)" desc="크롤링 작업 성공/실패" />}
        </section>
        <section className="card divide-y divide-line px-6 py-2">
          <Toggle checked={prefs.browser && perm === 'granted'} onChange={setBrowser} label="브라우저 알림"
            desc={perm === 'denied' ? '브라우저 설정에서 알림이 차단되어 있습니다.' : perm === 'unsupported' ? '이 브라우저는 알림을 지원하지 않습니다.' : '다른 탭을 보고 있을 때도 OS 알림으로 표시'} />
          <Toggle checked={prefs.sound} onChange={(v) => updatePrefs({ sound: v })} label="알림음" desc="이벤트 수신 시 짧은 알림음 재생" />
          <Toggle checked={dark} onChange={toggle} label="다크 모드" desc="에디토리얼 다크 테마" />
          <div className="flex items-center justify-between py-3 text-sm">
            <span>실시간 연결 상태</span>
            <span className="text-muted">{{ online: '연결됨', connecting: '연결 중', offline: '오프라인' }[status]}</span>
          </div>
        </section>
      </div>
    </>
  )
}
