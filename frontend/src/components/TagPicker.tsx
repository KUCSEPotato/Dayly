import { useEffect, useState } from 'react'
import { LoaderCircle, Plus, X } from 'lucide-react'
import { api } from '../lib/api'
import type { Tag } from '../types'

const palette = [
  { color: '#7c956b', name: '초록' }, { color: '#648ca6', name: '파랑' },
  { color: '#a183b5', name: '보라' }, { color: '#c48b65', name: '주황' },
  { color: '#bd7887', name: '분홍' }, { color: '#aa994f', name: '노랑' },
]

interface Props {
  selected: Tag[]
  onChange: (tags: Tag[]) => void
  disabled: boolean
  onCreating: (busy: boolean) => void
}

export function TagPicker({ selected, onChange, disabled, onCreating }: Props) {
  const [tags, setTags] = useState<Tag[]>([])
  const [query, setQuery] = useState('')
  const [color, setColor] = useState(palette[0].color)
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    api.tags(controller.signal).then(setTags).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '태그를 불러오지 못했습니다.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [revision])

  const normalized = query.trim().toLocaleLowerCase()
  const matches = tags.filter(tag => tag.name.toLocaleLowerCase().includes(normalized))
  const canCreate = normalized.length > 0 && !tags.some(tag => tag.name.toLocaleLowerCase() === normalized)
  const locked = disabled || creating

  function toggle(tag: Tag) {
    onChange(selected.some(item => item.id === tag.id) ? selected.filter(item => item.id !== tag.id) : [...selected, tag])
  }

  async function createTag() {
    if (locked || !canCreate) return
    setCreating(true)
    onCreating(true)
    setError(null)
    try {
      const tag = await api.createTag(query.trim(), color)
      setTags(current => current.some(item => item.id === tag.id) ? current : [...current, tag])
      if (!selected.some(item => item.id === tag.id)) onChange([...selected, tag])
      setQuery('')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '태그를 만들지 못했습니다.') }
    finally { setCreating(false); onCreating(false) }
  }

  return <fieldset className="tag-picker" disabled={locked}>
    <legend>태그 <span className="optional">선택</span></legend>
    {selected.length > 0 && <div className="selected-tags" aria-label="선택한 태그">{selected.map(tag =>
      <button type="button" className="tag-chip" key={tag.id} aria-label={`${tag.name} 태그 지정 해제`} onClick={() => toggle(tag)}>
        <span className="tag-color" style={{ backgroundColor: tag.color }} aria-hidden="true" />{tag.name}<X size={12} /></button>)}</div>}
    <label className="tag-search">태그 검색 또는 새 이름<input maxLength={30} value={query} onChange={event => setQuery(event.target.value)} placeholder="예: Python, Dayly" /></label>
    {loading ? <p className="tag-hint" role="status">태그를 불러오는 중이에요.</p> : <>
      <div className="tag-options" aria-label="기존 태그">{matches.map(tag =>
        <button type="button" className="tag-chip" aria-pressed={selected.some(item => item.id === tag.id)} key={tag.id} onClick={() => toggle(tag)}>
          <span className="tag-color" style={{ backgroundColor: tag.color }} aria-hidden="true" />{tag.name}</button>)}</div>
      {canCreate && <div className="new-tag">
        <div className="tag-palette" role="group" aria-label="새 태그 색상">{palette.map(item =>
          <label key={item.color} title={item.name}><input type="radio" name="tag-color" aria-label={item.name} value={item.color} checked={color === item.color} onChange={() => setColor(item.color)} /><span style={{ backgroundColor: item.color }} /></label>)}</div>
        <button className="text-button" type="button" onClick={() => void createTag()}><Plus size={14} />“{query.trim()}” 태그 만들기</button>
      </div>}
      {!tags.length && !normalized && !error && <p className="tag-hint">이름을 입력하면 새 태그를 만들 수 있어요.</p>}
    </>}
    {creating && <p role="status" className="tag-hint"><LoaderCircle size={13} className="spin" />태그를 저장하는 중이에요.</p>}
    {error && <div className="form-error" role="alert">{error}<button type="button" className="text-button" onClick={() => setRevision(value => value + 1)}>태그 다시 불러오기</button></div>}
  </fieldset>
}
