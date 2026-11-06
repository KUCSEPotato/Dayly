import { useEffect, useState } from 'react'
import { CalendarDays, Check, ChevronRight, CircleHelp, LayoutDashboard, LoaderCircle, RefreshCw, Sprout, X } from 'lucide-react'
import { Calendar } from './components/Calendar'
import { CompletionSummary } from './components/CompletionSummary'
import { TaskForm } from './components/TaskForm'
import { TaskList } from './components/TaskList'
import { WeeklyStatistics } from './components/WeeklyStatistics'
import { useDashboard } from './hooks/useDashboard'
import { api } from './lib/api'
import { formatDay, seoulToday, shiftMonth } from './lib/dates'
import type { Task, TaskInput } from './types'

export default function App() {
  const [today, setToday] = useState(seoulToday)
  const [date, setDate] = useState(today)
  const [month, setMonth] = useState(today.slice(0, 7))
  const [form, setForm] = useState<{ task?: Task } | null>(null)
  const [busy, setBusy] = useState(false)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [help, setHelp] = useState(false)
  const { data, loading, error, restricted, refresh } = useDashboard(date, month, today)

  useEffect(() => {
    const timer = window.setInterval(() => setToday(seoulToday()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  function selectDate(value: string) {
    setDate(value)
    setMonth(value.slice(0, 7))
    setMutationError(null)
  }

  async function mutate(action: () => Promise<unknown>): Promise<void> {
    setBusy(true)
    setMutationError(null)
    try { await action(); refresh() }
    catch (cause) { setMutationError(cause instanceof Error ? cause.message : '변경 사항을 저장하지 못했습니다.') }
    finally { setBusy(false) }
  }

  async function save(input: TaskInput): Promise<boolean> {
    // Throw to the form on failure so the user's input remains intact.
    if (form?.task) await api.update(form.task.id, input)
    else await api.create(input)
    refresh()
    return true
  }

  const visibleSummary = loading || error ? undefined : data?.calendar
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="Dayly 홈"><span className="brand-mark"><Check size={23} strokeWidth={2.6} /></span>dayly<span className="brand-period">.</span></a>
      <p className="brand-description">나를 위한 하루의 기록</p>
      <span className="nav-label">WORKSPACE</span>
      <button className="nav-item active" onClick={() => selectDate(today)}><LayoutDashboard size={18} />나의 하루<ChevronRight size={15} /></button>
      <div className="sidebar-note"><Sprout size={26} strokeWidth={1.4} /><p>서두르지 않아도 괜찮아요.<br />매일 조금씩 자라는 중이니까.</p><span>MAKE ROOM FOR YOURSELF</span></div>
      <button className="help-button" onClick={() => setHelp(value => !value)} aria-expanded={help}><CircleHelp size={17} />사용 안내</button>
      {help && <div className="help-content">달력에서 날짜를 선택하고 할 일을 추가하세요. 체크하면 달성률에 반영됩니다. 상세 기록은 최근 7일과 미래 날짜를 볼 수 있어요.</div>}
      <div className="profile"><span className="avatar">나</span><div><strong>나의 작은 워크스페이스</strong><span>Personal space</span></div><span className="online-dot" /></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div className="breadcrumb"><span>나의 워크스페이스</span><ChevronRight size={13} /><strong>나의 하루</strong></div><span className="topbar-date"><CalendarDays size={15} />{formatDay(today, { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}</span></header>
      <div className="page-content">
        <section className="page-intro"><div><div className="intro-eyebrow"><span />A FRESH LITTLE START</div><h1>오늘도, 나의 속도로<span>.</span></h1><p>작은 계획을 세우고, 하나씩 채워 가는 나다운 하루.</p></div>
          <CompletionSummary weekly={data?.weekly} loading={loading} error={Boolean(error)} /></section>
        {error ? <div className="error-banner" role="alert"><div><strong>기록을 불러오지 못했어요.</strong><p>{error}</p></div><button className="button button-quiet" onClick={refresh}><RefreshCw size={15} />다시 시도</button></div> : null}
        {mutationError && <div className="error-banner" role="alert"><p>{mutationError}</p><button className="icon-button" aria-label="오류 닫기" onClick={() => setMutationError(null)}><X size={18} /></button></div>}
        <div className="dashboard-grid">
          <Calendar month={month} selectedDate={date} today={today} summary={visibleSummary} onSelect={selectDate} onNavigate={offset => setMonth(value => shiftMonth(value, offset))} onToday={() => selectDate(today)} />
          {error ? <section className="panel tasks-panel"><div className="empty-state"><CircleHelp size={30} /><h2>연결을 확인해 주세요</h2><p>다시 시도하면 저장된 할 일을 불러옵니다.</p></div></section> :
            <TaskList date={date} today={today} tasks={data?.tasks ?? []} stats={data?.daily ?? null} restricted={restricted} loading={loading} busy={busy}
              onAdd={() => setForm({})} onEdit={task => setForm({ task })}
              onToggle={task => void mutate(() => api.update(task.id, { is_completed: !task.is_completed }))}
              onDelete={task => void mutate(() => api.delete(task.id))} />}
        </div>
        {!loading && !error && data && <WeeklyStatistics stats={data.weekly} selectedDate={date} onSelect={selectDate} />}
        {loading && <div className="panel statistics-loading" role="status"><LoaderCircle size={19} className="spin" />한 주의 기록을 불러오고 있어요.</div>}
        <footer className="page-footer"><span className="footer-brand">dayly.</span><span>하루를 채우는 작은 습관</span><span>Made for your everyday.</span></footer>
      </div>
    </main>
    {form && <TaskForm task={form.task} date={date} today={today} onSave={save} onClose={() => setForm(null)} />}
  </div>
}
