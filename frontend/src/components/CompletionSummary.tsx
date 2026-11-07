import { useState } from 'react'
import { ArrowUpRight, Sprout } from 'lucide-react'
import { rateLabel } from '../lib/dates'
import type { WeeklyStatistics } from '../types'

interface Props {
  weekly?: WeeklyStatistics
  loading: boolean
  error: boolean
  onOpenRetrospective: (kind: 'daily' | 'weekly') => void
}

export function CompletionSummary({ weekly, loading, error, onOpenRetrospective }: Props) {
  const [period, setPeriod] = useState<'today' | 'weekly'>('weekly')
  // Today comes from the existing weekly response, independent of the calendar selection.
  const stats = period === 'weekly' ? weekly : weekly?.days.find(day => day.date === weekly.end_date)
  const label = period === 'weekly' ? '최근 7일' : '오늘'
  const available = !loading && !error && stats !== undefined
  const rate = available ? stats.completion_rate : null
  const text = loading ? '불러오는 중' : error ? '연결 확인 필요' : rateLabel(rate)

  return <section className="completion-summary" aria-label="달성률 요약" aria-busy={loading}>
    <div className="summary-header"><div className="summary-switch" role="group" aria-label="달성률 기간">
      <button type="button" aria-pressed={period === 'today'} onClick={() => setPeriod('today')}>오늘</button>
      <button type="button" aria-pressed={period === 'weekly'} onClick={() => setPeriod('weekly')}>최근 7일</button>
    </div><button className="summary-open" aria-label={`${period === 'today' ? '일간' : '주간'} 회고 보기`} title="종료된 기간의 확정 회고 보기" onClick={() => onOpenRetrospective(period === 'today' ? 'daily' : 'weekly')}><ArrowUpRight size={17} /></button></div>
    <div className="summary-result">
      <Sprout size={22} strokeWidth={1.5} aria-hidden="true" />
      <div aria-live="polite"><span className="summary-label">{label} 달성률</span><strong>{text}</strong></div>
      <span className="summary-count" aria-label={`${label} 완료 및 전체 할 일`}>
        {available ? `${stats.completed} / ${stats.total}` : '—'}
      </span>
    </div>
    <div className="summary-progress" role="progressbar" aria-label={`${label} 달성률`}
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={rate ?? 0} aria-valuetext={text}>
      <div style={{ width: `${rate ?? 0}%` }} />
    </div>
  </section>
}
