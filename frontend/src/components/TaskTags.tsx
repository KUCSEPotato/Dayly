import type { Tag } from '../types'

export function TaskTags({ tags }: { tags?: Tag[] }) {
  if (!tags?.length) return null
  return <span className="task-tags" aria-label="지정된 태그">{tags.map(tag =>
    <span key={tag.id} className="tag-chip"><span className="tag-color" style={{ backgroundColor: tag.color }} aria-hidden="true" />{tag.name}</span>)}</span>
}
