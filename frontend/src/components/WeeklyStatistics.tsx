import { ArrowUpRight, ChartNoAxesColumnIncreasing, CircleCheck, ListTodo } from 'lucide-react'
import { formatDay, rateLabel } from '../lib/dates'
import type { WeeklyStatistics as WeeklyData } from '../types'

export function WeeklyStatistics({ stats, selectedDate, onSelect }: { stats: WeeklyData; selectedDate: string; onSelect: (date: string) => void }) {
  return <section className="panel weekly-panel" aria-labelledby="weekly-title">
    <div className="section-heading"><div><span className="eyebrow">YOUR WEEK, AT A GLANCE</span><h2 id="weekly-title">조금씩 쌓이는 나의 기록</h2></div>
      <span className="date-range">{formatDay(stats.start_date, { month: 'numeric', day: 'numeric' })} — {formatDay(stats.end_date, { month: 'numeric', day: 'numeric' })}<span>최근 7일</span></span></div>
    <div className="weekly-content">
      <div className="weekly-overview"><span className="overview-label"><ChartNoAxesColumnIncreasing size={16} />주간 달성률</span>
        <div className="weekly-rate">{stats.completion_rate === null ? <span className="no-record">기록 없음</span> : <>{Math.round(stats.completion_rate)}<span>%</span></>}</div>
        <p>{stats.total ? '하나씩 해낸 만큼, 한 걸음 더.' : '이번 주의 첫 기록을 만들어 보세요.'}</p>
        <div className="weekly-counts"><span><CircleCheck size={15} />완료 <strong>{stats.completed}</strong></span><span><ListTodo size={15} />전체 <strong>{stats.total}</strong></span></div>
      </div>
      <div className="chart" role="group" aria-label="최근 7일 일일 달성률">
        <div className="chart-axis" aria-hidden="true"><span>100%</span><span>50%</span><span>0%</span></div>
        <div className="chart-plot"><div className="chart-grid" aria-hidden="true"><i /><i /><i /></div>
          <div className="chart-bars">{stats.days.map(day => <button className={`chart-column ${day.date === selectedDate ? 'active' : ''}`} key={day.date}
            onClick={() => onSelect(day.date)} aria-label={`${day.date}, ${day.completed}/${day.total}개 완료, ${rateLabel(day.completion_rate)}`}>
            <div className="bar-area"><span className="bar-value">{day.completion_rate === null ? '—' : `${Math.round(day.completion_rate)}%`}</span>
              <div className={`chart-bar ${day.completion_rate === 100 ? 'full' : (day.completion_rate ?? 0) >= 50 ? 'medium' : 'low'} ${day.completion_rate === null ? 'empty' : ''}`}
                style={{ height: day.completion_rate ? `${day.completion_rate}%` : '3px' }} /></div>
            <span className="chart-day">{formatDay(day.date, { weekday: 'short' })}{day.date === stats.end_date && <i />}</span>
            <span className="chart-date">{formatDay(day.date, { month: 'numeric', day: 'numeric' })}</span>
            <span className="chart-count">{day.total ? `${day.completed}/${day.total}` : '기록 없음'}</span>
          </button>)}</div>
        </div>
      </div>
    </div>
    <div className="weekly-footer"><span><i className="legend-dot done" />완료 비율이 높을수록 진한 초록색으로 표시돼요.</span><span>날짜를 눌러 기록 보기 <ArrowUpRight size={13} /></span></div>
  </section>
}
