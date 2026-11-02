import { ChevronLeft, ChevronRight } from 'lucide-react'
import { addDays, asDate, formatDay } from '../lib/dates'
import type { CalendarSummary } from '../types'

interface Props {
  month: string
  selectedDate: string
  today: string
  summary?: CalendarSummary
  onSelect: (date: string) => void
  onNavigate: (offset: number) => void
  onToday: () => void
}

export function Calendar({ month, selectedDate, today, summary, onSelect, onNavigate, onToday }: Props) {
  const first = `${month}-01`
  const start = addDays(first, -asDate(first).getUTCDay())
  const counts = new Map(summary?.days.map(day => [day.date, day]))
  return <section className="panel calendar-panel" aria-labelledby="calendar-title">
    <div className="section-heading">
      <div><span className="eyebrow">PLAN YOUR DAYS</span><h2 id="calendar-title">나의 달력</h2></div>
      <button className="button button-small button-quiet" onClick={onToday}>오늘로</button>
    </div>
    <div className="month-navigation">
      <h3>{formatDay(first, { year: 'numeric', month: 'long' })}</h3>
      <div className="flex gap-1">
        <button className="icon-button" aria-label="이전 달" onClick={() => onNavigate(-1)} disabled={month === '0001-01'}><ChevronLeft size={19} /></button>
        <button className="icon-button" aria-label="다음 달" onClick={() => onNavigate(1)} disabled={month === '9999-12'}><ChevronRight size={19} /></button>
      </div>
    </div>
    <div className="calendar-grid weekdays" aria-hidden="true">
      {['일', '월', '화', '수', '목', '금', '토'].map((day, index) => <span className={index === 0 ? 'sunday' : ''} key={day}>{day}</span>)}
    </div>
    <div className="calendar-grid" role="group" aria-label="날짜 선택">
      {Array.from({ length: 42 }, (_, index) => {
        const date = addDays(start, index)
        const day = counts.get(date)
        const inMonth = date.startsWith(month)
        return <button key={date} type="button"
          className={`calendar-day ${!inMonth ? 'outside-month' : ''} ${date === selectedDate ? 'selected' : ''} ${date === today ? 'is-today' : ''}`}
          aria-label={`${date}${day?.total ? `, ${day.total}개 중 ${day.completed}개 완료` : ''}`}
          aria-pressed={date === selectedDate}
          onClick={() => onSelect(date)}>
          <span className="day-number">{asDate(date).getUTCDate()}</span>
          {Boolean(day?.total) && <span className={`day-badge ${day!.total === day!.completed ? 'all-done' : ''}`}>{day!.completed}/{day!.total}</span>}
          {date === today && !day?.total && <span className="today-dot" />}
        </button>
      })}
    </div>
    <div className="calendar-legend"><span><i className="legend-dot" />할 일 있음</span><span><i className="legend-dot done" />모두 완료</span><span className="timezone-label">Asia/Seoul</span></div>
  </section>
}
