import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, X } from 'lucide-react'
import { addDays } from '../lib/dates'
import type { Task, TaskInput } from '../types'

interface Props {
  task?: Task
  date: string
  today: string
  onSave: (data: TaskInput) => Promise<boolean>
  onClose: () => void
}

export function TaskForm({ task, date, today, onSave, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [scheduledDate, setScheduledDate] = useState(task?.scheduled_date ?? date)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const dialog = dialogRef.current!
    dialog.showModal()
    return () => dialog.close()
  }, [])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!title.trim()) { setError('할 일 제목을 입력해 주세요.'); return }
    setSaving(true)
    setError(null)
    try {
      if (await onSave({ title: title.trim(), description: description.trim() || null, scheduled_date: scheduledDate })) onClose()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '저장하지 못했습니다.')
    } finally { setSaving(false) }
  }

  return <dialog ref={dialogRef} className="task-dialog" aria-labelledby="form-title" onCancel={event => {
    event.preventDefault(); if (!saving) onClose()
  }}>
    <div className="section-heading"><div><span className="eyebrow">ONE SMALL STEP</span><h2 id="form-title">{task ? '할 일 수정' : '새로운 할 일'}</h2></div>
      <button className="icon-button" aria-label="닫기" onClick={onClose} disabled={saving}><X size={20} /></button></div>
    <form onSubmit={submit} className="task-form">
      <label>할 일 제목 <span className="required">*</span><input autoFocus required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} placeholder="어떤 하루를 만들고 싶나요?" disabled={saving} /></label>
      <label>상세 설명 <span className="optional">선택</span><textarea maxLength={5000} rows={3} value={description} onChange={e => setDescription(e.target.value)} placeholder="기억해 두고 싶은 내용을 적어 주세요." disabled={saving} /></label>
      <label>예정 날짜<input type="date" required min={addDays(today, -6)} max="9999-12-31" value={scheduledDate} onChange={e => setScheduledDate(e.target.value)} disabled={saving} /></label>
      {error && <p role="alert" className="form-error">{error}</p>}
      <div className="form-actions"><button className="button button-quiet" type="button" disabled={saving} onClick={onClose}>취소</button>
        <button className="button button-primary" disabled={saving || !title.trim()} type="submit">{saving && <LoaderCircle size={16} className="spin" />}{saving ? '저장 중…' : task ? '변경 저장' : '할 일 추가'}</button></div>
    </form>
  </dialog>
}
