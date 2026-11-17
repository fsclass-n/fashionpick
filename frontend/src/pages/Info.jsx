import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faChevronDown, faEnvelope, faHeadset } from '@fortawesome/free-solid-svg-icons'
import { SITE } from '../lib/site'

function Doc({ title, updated, sections }) {
  return (
    <div className="container-x max-w-3xl pt-10 md:pt-16">
      <h1 className="text-[28px] font-bold tracking-tight md:text-[36px]">{title}</h1>
      <p className="mt-2 text-[13px] text-muted">시행일 {updated} · 포트폴리오 데모 서비스용 문서입니다.</p>
      <div className="mt-10 space-y-9">
        {sections.map(([h, body]) => (
          <section key={h}>
            <h2 className="text-[16px] font-bold">{h}</h2>
            <p className="mt-3 text-[14px] leading-7 whitespace-pre-line text-muted">{body}</p>
          </section>
        ))}
      </div>
    </div>
  )
}

export function Terms() {
  return (
    <Doc title="이용약관" updated="2026-11-01" sections={[
      ['제1조 (목적)', `이 약관은 ${SITE.company}(이하 "회사")가 운영하는 fashionpick(이하 "서비스")의 이용 조건과 절차, 회사와 회원의 권리·의무를 정합니다.`],
      ['제2조 (회원가입)', '회원은 이메일 또는 소셜 계정(Google·네이버·카카오)으로 가입할 수 있으며, 비밀번호는 영문 대문자·소문자, 숫자, 특수문자를 포함해 8자 이상이어야 합니다.'],
      ['제3조 (주문과 발주)', '회원이 주문하면 회사는 상품 공급처별로 발주서를 자동 작성해 발송합니다. 주문 상태(주문 접수 → 발주 진행 → 발주 완료 → 입고)는 마이페이지에서 확인할 수 있습니다.'],
      ['제4조 (청약 철회)', '회원은 상품을 받은 날부터 7일 이내에 청약을 철회할 수 있습니다. 다만 착용 흔적이 있거나 택이 제거된 경우 제한될 수 있습니다.'],
      ['제5조 (데모 서비스 고지)', '본 서비스는 4인 팀 포트폴리오용 데모로, 실제 결제와 배송은 이루어지지 않습니다.'],
    ]} />
  )
}

export function Privacy() {
  return (
    <Doc title="개인정보처리방침" updated="2026-11-01" sections={[
      ['1. 수집 항목', '필수: 이메일, 이름, 비밀번호(단방향 암호화 저장)\n주문 시: 받는 분 이름, 연락처, 배송지\n소셜 로그인 시: 제공자 식별자, 이메일, 닉네임'],
      ['2. 이용 목적', '회원 식별, 주문 처리와 공급처 발주, 주문 상태 알림, 고객 문의 응대'],
      ['3. 보관 기간', '회원 탈퇴 시 지체 없이 파기합니다. 단, 전자상거래법에 따른 거래 기록은 5년간 보관합니다.'],
      ['4. 제3자 제공', '주문 상품의 출고를 위해 해당 공급처에 상품·수량·옵션 정보를 담은 발주서를 제공합니다.'],
      ['5. 개인정보 보호책임자', `${SITE.privacyOfficer} · ${SITE.cs.email}`],
    ]} />
  )
}

const FAQ = [
  ['주문 후 배송은 언제 시작되나요?', '주문이 접수되면 공급처별 발주서가 자동으로 작성·발송되고, 공급처 출고 후 2~3일 안에 받아보실 수 있습니다.'],
  ['주문 상태는 어디서 확인하나요?', '마이페이지 > 주문 내역에서 확인할 수 있으며, 상태가 바뀌면 실시간 알림으로도 알려드립니다.'],
  ['트렌드 키워드는 어떻게 정해지나요?', 'RPA가 네이버 데이터랩 쇼핑인사이트와 패션 랭킹 페이지를 매시간 수집해 순위를 매깁니다.'],
  ['테스트 관리자와 실제 관리자는 무엇이 다른가요?', '테스트 관리자는 관리자 화면을 모두 볼 수 있지만 데이터 생성·수정·삭제는 막혀 있습니다. 실제 관리자는 서버에 설정된 ADMIN_TOKEN으로 인증해 모든 권한을 가집니다.'],
]

export function Support() {
  const [open, setOpen] = useState(0)
  return (
    <div className="container-x pt-10 md:pt-16">
      <h1 className="text-[28px] font-bold tracking-tight md:text-[36px]">고객센터</h1>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="border border-line p-6">
          <FontAwesomeIcon icon={faHeadset} className="text-xl" />
          <p className="mt-4 text-[13px] text-muted">전화 상담</p>
          <p className="text-3xl font-bold tracking-tight">{SITE.cs.phone}</p>
          <p className="mt-2 text-[13px] text-muted">{SITE.cs.hours} · {SITE.cs.lunch} · {SITE.cs.closed}</p>
        </div>
        <div className="border border-line p-6">
          <FontAwesomeIcon icon={faEnvelope} className="text-xl" />
          <p className="mt-4 text-[13px] text-muted">이메일 문의</p>
          <a href={`mailto:${SITE.cs.email}`} className="text-2xl font-bold tracking-tight hover:underline">{SITE.cs.email}</a>
          <p className="mt-2 text-[13px] text-muted">영업일 기준 24시간 안에 답변드립니다.</p>
        </div>
      </div>

      <section id="faq" className="mt-14 scroll-mt-36">
        <h2 className="section-title">자주 묻는 질문</h2>
        <div className="mt-5 border-t border-fg">
          {FAQ.map(([q, a], i) => (
            <div key={q} className="border-b border-line">
              <button onClick={() => setOpen(open === i ? -1 : i)} className="flex w-full items-center justify-between py-4 text-left text-[14px] font-medium" aria-expanded={open === i}>
                <span><b className="mr-3 text-accent">Q</b>{q}</span>
                <FontAwesomeIcon icon={faChevronDown} className={`text-xs text-muted transition ${open === i ? 'rotate-180' : ''}`} />
              </button>
              {open === i && <p className="pb-5 pl-7 text-[14px] leading-7 text-muted">{a}</p>}
            </div>
          ))}
        </div>
      </section>

      <section id="about" className="mt-14 scroll-mt-36">
        <h2 className="section-title">회사 소개</h2>
        <p className="mt-4 max-w-2xl text-[14px] leading-7 text-muted">
          fashionpick은 RPA로 패션 트렌드 키워드를 수집하고, 도매 상품을 소싱하고, 주문이 들어오면 발주서까지 자동으로 작성하는 패션 셀렉트숍입니다.
          박미금(조장), 김모란, 이오리, 홍기흥 4인이 만든 팀 프로젝트입니다.
        </p>
      </section>
    </div>
  )
}
