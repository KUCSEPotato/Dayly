// Calendar dates are date-only strings. Never parse them in the browser's local timezone.
export function seoulToday(): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const part = (type: string) => parts.find(p => p.type === type)!.value
  return `${part('year')}-${part('month')}-${part('day')}`
}

export function asDate(value: string): Date {
  return new Date(`${value}T00:00:00Z`)
}

export function addDays(value: string, days: number): string {
  const day = asDate(value)
  day.setUTCDate(day.getUTCDate() + days)
  return day.toISOString().slice(0, 10)
}

export function formatDay(value: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat('ko-KR', { ...options, timeZone: 'UTC' }).format(asDate(value))
}

export function shiftMonth(value: string, offset: number): string {
  const day = asDate(`${value}-01`)
  day.setUTCMonth(day.getUTCMonth() + offset)
  return day.toISOString().slice(0, 7)
}

export function rateLabel(rate: number | null): string {
  return rate === null ? '기록 없음' : `${Math.round(rate)}%`
}
