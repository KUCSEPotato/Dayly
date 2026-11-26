import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CalendarArrowUp, CalendarDays, LoaderCircle, X } from 'lucide-react'
import { addDays } from '../lib/dates'
import type { Task } from '../types'

interface Props {
  task: Task
  busy: boolean
  onPostpone: (targetDate?: string) => Promise<boolean>
}

export function PostponeMenu({ task, busy, onPostpone }: Props) {
  const [open, setOpen] = useState(false)
  const [customDate, setCustomDate] = useState(false)
  const [targetDate, setTargetDate] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [position, setPosition] = useState({ left: 0, top: 0 })
  const pending = useRef(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const panelId = useId()
  const atLimit = task.scheduled_date === '9999-12-31'
  const minimum = atLimit ? task.scheduled_date : addDays(task.scheduled_date, 1)
  const locked = busy || submitting

  function close(restoreFocus = false) {
    if (pending.current) return
    setOpen(false)
    if (restoreFocus) trigger.current?.focus()
  }

  useLayoutEffect(() => {
    if (!open) return
    const place = () => {
      const button = trigger.current?.getBoundingClientRect()
      const popup = panel.current?.getBoundingClientRect()
      if (!button || !popup) return
      const left = Math.max(8, Math.min(button.right - popup.width, window.innerWidth - popup.width - 8))
      const below = button.bottom + 8
      const preferredTop = below + popup.height <= window.innerHeight - 8 ? below : button.top - popup.height - 8
      const top = Math.max(8, Math.min(preferredTop, window.innerHeight - popup.height - 8))
      setPosition({ left, top })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => { window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true) }
  }, [open, customDate])

  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => {
      if (!trigger.current?.contains(event.target as Node) && !panel.current?.contains(event.target as Node)) close()
    }
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') close(true) }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [open])

  useEffect(() => { if (customDate) input.current?.focus() }, [customDate])
  useEffect(() => { if (open) panel.current?.querySelector<HTMLButtonElement>('.postpone-option')?.focus() }, [open])

  async function submit(date?: string) {
    if (locked || pending.current || atLimit) return
    if (date !== undefined && date <= task.scheduled_date) return
    pending.current = true
    setSubmitting(true)
    try { if (await onPostpone(date)) setOpen(false) }
    finally { pending.current = false; setSubmitting(false) }
  }

  return <>
    <button ref={trigger} type="button" className="icon-button" aria-label={`${task.title} 미루기`} title="미루기"
      aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? panelId : undefined}
      disabled={locked || task.is_completed} onClick={() => { setCustomDate(false); setTargetDate(''); setOpen(value => !value) }}><CalendarArrowUp size={15} /></button>
    {open && createPortal(<div ref={panel} id={panelId} className="postpone-popover" role="dialog" aria-label={`${task.title} 미루기`} style={position}>
      <div className="postpone-heading"><strong>할 일 미루기</strong><button type="button" className="icon-button" aria-label="미루기 닫기" onClick={() => close(true)} disabled={locked}><X size={15} /></button></div>
      <button type="button" className="postpone-option" disabled={locked || atLimit} onClick={() => void submit()}><CalendarArrowUp size={16} />다음 날로 미루기</button>
      <button type="button" className="postpone-option" disabled={locked || atLimit} aria-expanded={customDate} onClick={() => setCustomDate(true)}><CalendarDays size={16} />날짜 직접 지정</button>
      {atLimit ? <p className="postpone-hint">더 이상 미룰 수 없는 날짜예요.</p> : customDate && <form className="postpone-date-form" onSubmit={event => { event.preventDefault(); if (targetDate) void submit(targetDate) }}>
        <label>미룰 날짜<input ref={input} type="date" min={minimum} max="9999-12-31" required value={targetDate} onChange={event => setTargetDate(event.target.value)} disabled={locked} /></label>
        <p className="postpone-hint">기존 예정 날짜 이후만 선택할 수 있어요. 이전 날짜로 옮기려면 수정을 이용해 주세요.</p>
        <button type="submit" className="button button-primary button-small" disabled={locked || !targetDate || targetDate <= task.scheduled_date}>{submitting && <LoaderCircle size={14} className="spin" />}미루기 확인</button>
      </form>}
    </div>, document.body)}
  </>
}
