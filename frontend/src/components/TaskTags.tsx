import type { Tag } from '../types'
import { tagStyle } from '../lib/tags'

export function TaskTags({ tags }: { tags?: Tag[] }) {
  if (!tags?.length) return null
  return <span className="task-tags" aria-label="지정된 태그">{tags.map(tag =>
    <span key={tag.id} className="tag-chip" style={tagStyle(tag.color)}>{tag.name}</span>)}</span>
}
