import { useState } from 'react'
import { Check, LoaderCircle, Pencil, Trash2 } from 'lucide-react'
import type { Task } from '../types'
import { TaskTags } from './TaskTags'
import { PostponeMenu } from './PostponeMenu'

interface Props {
  task: Task
  busy: boolean
  onToggle: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
  onPostpone: (task: Task, targetDate?: string) => Promise<boolean>
}

export function TaskItem({ task, busy, onToggle, onEdit, onDelete, onPostpone }: Props) {
  const [confirming, setConfirming] = useState(false)
  return <li className={`task-item ${task.is_completed ? 'completed' : ''}`}>
    <button className="task-checkbox" role="checkbox" aria-checked={task.is_completed}
      aria-label={`${task.title} 완료`} onClick={() => onToggle(task)} disabled={busy}>
      {busy ? <LoaderCircle size={15} className="spin" /> : task.is_completed ? <Check size={16} strokeWidth={3} /> : null}
    </button>
    <div className="task-content"><div className="task-title-line"><TaskTags tags={task.tags} /><span className="task-title">{task.title}</span></div>{task.description && <p>{task.description}</p>}
      {confirming && <div className="delete-confirm"><span>이 할 일을 삭제할까요?</span><button disabled={busy} onClick={() => onDelete(task)}>삭제</button><button disabled={busy} onClick={() => setConfirming(false)}>취소</button></div>}
    </div>
    <div className="task-actions"><button className="icon-button" aria-label={`${task.title} 수정`} disabled={busy} onClick={() => onEdit(task)}><Pencil size={15} /></button>
      <PostponeMenu task={task} busy={busy} onPostpone={targetDate => onPostpone(task, targetDate)} />
      <button className="icon-button delete-button" aria-label={`${task.title} 삭제`} disabled={busy} onClick={() => setConfirming(value => !value)}><Trash2 size={15} /></button></div>
  </li>
}
