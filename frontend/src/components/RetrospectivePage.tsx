import { useEffect, useState } from 'react'
import { BookOpen, Check, ChevronLeft, ChevronRight, Circle, Clock3, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { addDays, asDate, formatDay, rateLabel, seoulToday } from '../lib/dates'
import type { RetrospectiveKind, RetrospectiveList, Task } from '../types'

const labels = { daily: '일간', weekly: '주간', monthly: '월간' }

function latestStart(kind: RetrospectiveKind, today: string): string {
  if (kind === 'daily') return addDays(today, -1)
  if (kind === 'monthly') return addDays(today.slice(0, 7) + '-01', -1).slice(0, 7) + '-01'
  const weekday = (asDate(today).getUTCDay() + 6) % 7
  return addDays(today, -weekday - 7)
}

function SnapshotTasks({ tasks, completed }: { tasks: Task[]; completed: boolean }) {
  return <section className="panel retrospective-tasks">
    <h2>{completed ? '완료한 일' : '미완료한 일'} <span>{tasks.length}</span></h2>
    {tasks.length ? <ul>{tasks.map((task, index) => <li key={`${task.id}-${task.scheduled_date}-${index}`}>
      {completed ? <Check size={16} /> : <Circle size={14} />}<div><strong>{task.title}</strong>
        {task.description && <p>{task.description}</p>}<span>{formatDay(task.scheduled_date, { month: 'long', day: 'numeric' })} 예정</span></div>
    </li>)}</ul> : <p className="quiet-empty">이 기간에 해당하는 항목이 없어요.</p>}
  </section>
}

export function RetrospectivePage({ kind, onKindChange }: { kind: RetrospectiveKind; onKindChange: (kind: RetrospectiveKind) => void }) {
  const [anchor, setAnchor] = useState<string>()
  const [data, setData] = useState<RetrospectiveList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(null)
    api.retrospectives(kind, anchor, controller.signal).then(result => {
      if (!controller.signal.aborted) setData(result)
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '회고를 불러오지 못했습니다.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [kind, anchor, revision])
  const period = data?.requested_period
  const snapshot = data?.items.find(item => item.period_start === period?.start)
  const status = data?.status
  const rate = snapshot?.completion_rate ?? null
  return <div className="retrospective-page">
    <section className="feature-intro"><span className="eyebrow">LOOK BACK, MOVE FORWARD</span><h1>나만의 회고<span>.</span></h1>
      <p>{kind === 'daily' ? '하루가 끝난 시점의 확정 기록이에요. 처음에는 가장 최근에 종료된 날짜를 보여 드려요.' : kind === 'weekly' ? '월요일부터 일요일까지, 날짜별 확정 기록을 모았어요.' : '달력의 1일부터 말일까지, 날짜별 확정 기록을 모았어요.'}</p></section>
    <div className="retrospective-tabs" role="tablist" aria-label="회고 종류">{(['daily', 'weekly', 'monthly'] as const).map(value =>
      <button key={value} role="tab" aria-selected={kind === value} onClick={() => onKindChange(value)}>{labels[value]} 회고</button>)}</div>
    <div className="period-toolbar"><div className="period-buttons">
      <button className="icon-button" aria-label="이전 회고" disabled={!period || loading} onClick={() => setAnchor(addDays(period!.start, -1))}><ChevronLeft size={20} /></button>
      <strong>{period ? `${formatDay(period.start, { year: 'numeric', month: 'long', day: 'numeric' })}${kind === 'daily' ? '' : ' — ' + formatDay(addDays(period.end, -1), { month: 'long', day: 'numeric' })}` : '기간 확인 중'}</strong>
      <button className="icon-button" aria-label="다음 회고" disabled={!period || loading || period.start >= latestStart(kind, seoulToday())} onClick={() => setAnchor(period!.end)}><ChevronRight size={20} /></button>
    </div><button className="button button-small button-quiet" onClick={() => setAnchor(undefined)}>최근 회고</button></div>
    {error && <div className="error-banner" role="alert"><p>{error}</p><button className="button button-quiet" onClick={() => setRevision(value => value + 1)}><RefreshCw size={15} />다시 시도</button></div>}
    {loading ? <div className="panel statistics-loading" role="status"><LoaderCircle className="spin" size={18} />확정된 기록을 불러오는 중이에요.</div> : !error && <>
      {status === 'not_ended' && <div className="panel feature-empty"><Clock3 /><h2>아직 끝나지 않은 기간이에요</h2><p>기간이 완전히 종료된 후 고정 회고를 확인할 수 있어요.</p></div>}
      {status === 'unavailable' && <div className="coverage-notice" role="status"><BookOpen size={20} /><div><strong>기록 복원 불가</strong><p>변경 이력을 추적하기 전의 기간이에요. 활동이 없었던 기간과는 달라요.</p></div></div>}
      {status === 'partial' && <div className="coverage-notice" role="status"><BookOpen size={20} /><div><strong>일부 기록만 확인 가능</strong><p>이력 추적을 시작한 뒤의 기록만 포함되어 있어요. 전체 달성률로 해석하지 말아 주세요.</p></div></div>}
      {status === 'no_activity' && <div className="panel feature-empty"><BookOpen /><h2>활동 기록 없음</h2><p>아직 작성된 회고가 없어요. 할 일을 정리하고 하루를 보내면 첫 번째 회고가 만들어져요.</p></div>}
      {snapshot && <>
        <section className="panel retrospective-overview" aria-label="고정 회고 요약"><div className="snapshot-tag"><Clock3 size={13} />확정된 {labels[kind]} 기록</div>
          <h2>{status === 'unavailable' ? '이 기간의 정확한 활동은 알 수 없어요.' : `총 ${snapshot.total}개의 할 일 중 ${snapshot.completed}개를 완료했어요.`}</h2>
          <div className="retrospective-metrics"><div><span>최종 달성률{status === 'partial' ? ' · 일부 기록' : ''}</span><strong>{status === 'unavailable' ? '복원 불가' : status === 'partial' && rate === null ? '일부 기록' : rateLabel(rate)}</strong></div>
            <div><span>완료 / 전체</span><strong>{snapshot.completed ?? '—'} <small>/ {snapshot.total ?? '—'}</small></strong></div>
            <div><span>획득 경험치</span><strong>{snapshot.xp_total}<small> XP</small></strong></div></div>
          <div className="progress-track" role="progressbar" aria-label="고정 회고 달성률" aria-valuemin={0} aria-valuemax={100} aria-valuenow={rate ?? 0} aria-valuetext={status === 'unavailable' ? '기록 복원 불가' : rateLabel(rate)}><div className="progress-fill" style={{ width: `${rate ?? 0}%` }} /></div>
          <p className="snapshot-footnote">생성된 회고는 할 일을 수정하거나 삭제해도 바뀌지 않아요. · 실제 최초 완료 {snapshot.data.activity.unique_completed_tasks}개</p>
        </section>
        {status !== 'unavailable' && <>
          <section className="panel retrospective-chart"><div className="section-heading"><h2>날짜별 확정 달성률</h2>{snapshot.data.best_day && <span className="best-day"><Sparkles size={13} />가장 많이 해낸 날 {formatDay(snapshot.data.best_day, { month: 'numeric', day: 'numeric' })}</span>}</div>
            <div className="retro-chart-scroll"><div className="retro-bars" role="group" aria-label="회고 날짜별 달성률" style={{ gridTemplateColumns: `repeat(${snapshot.data.days.length}, minmax(32px, 1fr))` }}>
              {snapshot.data.days.map(day => <div className="retro-bar-column" key={day.date} aria-label={`${day.date}, ${day.coverage === 'unavailable' ? '기록 복원 불가' : rateLabel(day.completion_rate)}`}>
                <span>{day.coverage === 'unavailable' ? '?' : day.completion_rate === null ? '—' : `${Math.round(day.completion_rate)}%`}</span><div className="retro-bar-space"><i style={{ height: `${day.completion_rate ?? 0}%` }} /></div>
                <strong>{formatDay(day.date, { month: 'numeric', day: 'numeric' })}</strong><small>{day.total === null ? '복원 불가' : day.total ? `${day.completed}/${day.total}` : '기록 없음'}</small>
              </div>)}
            </div></div>
            {kind === 'monthly' && <div className="month-week-stats">{snapshot.data.weeks.map(week => <div key={week.start}><span>{formatDay(week.start, { month: 'numeric', day: 'numeric' })} 주</span><strong>{week.completed}/{week.total}개 완료</strong><span>{rateLabel(week.completion_rate)}</span></div>)}</div>}
          </section>
          <div className="snapshot-task-grid"><SnapshotTasks tasks={snapshot.data.completed_tasks} completed /><SnapshotTasks tasks={snapshot.data.incomplete_tasks} completed={false} /></div>
        </>}
      </>}
    </>}
  </div>
}
