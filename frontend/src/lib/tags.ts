import type { CSSProperties } from 'react'

export function tagStyle(color: string): CSSProperties {
  return { '--tag-color': color } as CSSProperties
}
