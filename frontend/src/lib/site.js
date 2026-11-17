// 푸터·고객센터·정책 페이지에 쓰는 사이트 정보 (포트폴리오 데모 값)
export const SITE = {
  name: 'fashionpick',
  company: '(주)패션픽 (데모)',
  ceo: '박미금',
  privacyOfficer: '김모란',
  bizNo: '000-00-00000 (데모)',
  mailOrderNo: '제2026-서울성동-0000호 (데모)',
  address: '서울특별시 성동구 성수이로 (데모 주소)',
  hosting: 'Render · Netlify',
  cs: {
    phone: '1588-0000',
    hours: '평일 10:00 - 18:00',
    lunch: '점심 12:00 - 13:00',
    closed: '주말·공휴일 휴무',
    email: 'help@fashionpick.dev',
  },
}

// 공식 계정이 확정되면 url 을 채운다. (url 이 없으면 '준비 중'으로 비활성 표시)
export const SNS = [
  { id: 'instagram', label: 'Instagram', url: import.meta.env.VITE_SNS_INSTAGRAM || '' },
  { id: 'youtube', label: 'YouTube', url: import.meta.env.VITE_SNS_YOUTUBE || '' },
  { id: 'kakao', label: '카카오톡 채널', url: import.meta.env.VITE_SNS_KAKAO || '' },
  { id: 'github', label: 'GitHub', url: 'https://github.com/fsclass-n/fashionpick' },
]

export const MAIN_NAV = [
  { to: '/shop', label: 'SHOP' },
  { to: '/shop?sort=new', label: 'NEW' },
  { to: '/shop?sort=trend', label: 'BEST' },
  { to: '/trends', label: 'TREND' },
  { to: '/#lookbook', label: 'LOOKBOOK' },
]

export const ROLE_LABEL = { user: '일반 회원', admin: '관리자', test_admin: '테스트 관리자' }
export const READ_ONLY_TIP = '테스트 관리자는 읽기 전용입니다'
