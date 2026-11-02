import { Check, Leaf, LockKeyhole, Plus } from 'lucide-react'
import { formatDay } from '../lib/dates'
import type { DailyStatistics, Task } from '../types'
import { DailyProgress } from './DailyProgress'
import { TaskItem } from './TaskItem'

interface Props {
  date: string
  today: string
  tasks: Task[]
  stats: DailyStatistics | null
  restricted: boolean
  loading: boolean
  busy: boolean
  onAdd: () => void
  onToggle: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}

export function TaskList(props: Props) {
  const { date, today, tasks, stats, restricted, loading, busy } = props
  const pending = tasks.filter(task => !task.is_completed)
  const completed = tasks.filter(task => task.is_completed)
  return <section className="panel tasks-panel" aria-labelledby="tasks-title" aria-busy={loading}>
    <div className="section-heading"><div><span className="eyebrow">A LITTLE EVERY DAY</span>
      <h2 id="tasks-title">{formatDay(date, { month: 'long', day: 'numeric', weekday: 'long' })}{date === today && <span className="today-pill">오늘</span>}</h2></div>
      <button className="button button-primary button-small" disabled={restricted || busy || loading} onClick={props.onAdd}><Plus size={16} />할 일 추가</button>
    </div>
    {loading ? <div role="status" className="empty-state"><span className="loading-dot" />하루를 불러오는 중이에요.</div> : restricted ?
      <div className="empty-state"><div className="empty-icon"><LockKeyhole size={26} /></div><h3>지난 기록은 달력에 남아 있어요</h3><p>상세 기록은 오늘을 포함한 최근 7일간 볼 수 있어요.<br />이전 날짜의 완료 현황은 달력에서 확인해 주세요.</p></div> : <>
        {stats && <DailyProgress stats={stats} />}
        {tasks.length === 0 ? <div className="empty-state"><div className="empty-icon"><Leaf size={29} strokeWidth={1.5} /></div><h3>아직 비어 있는 하루</h3><p>작은 할 일 하나로 하루를 시작해 보세요.<br />차근차근, 나만의 속도로 채워 가면 돼요.</p><button className="text-button" onClick={props.onAdd}><Plus size={15} />첫 번째 할 일 추가하기</button></div> :
          <div className="task-groups">{[{ label: '해야 할 일', items: pending }, { label: '완료한 일', items: completed }].map(group => group.items.length > 0 && <div key={group.label}>
            <h3 className="task-group-title">{group.label}<span>{group.items.length}</span></h3>
            <ul>{group.items.map(task => <TaskItem key={task.id} task={task} busy={busy} onToggle={props.onToggle} onEdit={props.onEdit} onDelete={props.onDelete} />)}</ul>
          </div>)}
            {pending.length === 0 && <div className="all-complete"><Check size={16} />오늘의 할 일을 모두 마쳤어요. 수고했어요!</div>}
          </div>}
      </>}
    <div className="task-footer"><span className="tiny-spark">✧</span> 작은 실천이 모여, 나다운 하루가 됩니다.</div>
  </section>
}
