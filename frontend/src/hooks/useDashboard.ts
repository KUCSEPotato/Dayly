import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { addDays } from '../lib/dates'
import type { CalendarSummary, DailyStatistics, Task, WeeklyStatistics } from '../types'

interface DashboardData {
  tasks: Task[]
  daily: DailyStatistics | null
  calendar: CalendarSummary
  weekly: WeeklyStatistics
}

export function useDashboard(date: string, month: string, today: string) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const restricted = date < addDays(today, -6)
  const refresh = useCallback(() => setRevision(value => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    setLoading(true)
    setError(null)
    Promise.all([
      restricted ? Promise.resolve([] as Task[]) : api.tasks(date, signal),
      restricted ? Promise.resolve(null) : api.daily(date, signal),
      api.calendar(month, signal),
      api.weekly(signal),
    ]).then(([tasks, daily, calendar, weekly]) => {
      if (!signal.aborted) setData({ tasks, daily, calendar, weekly })
    }).catch((cause: unknown) => {
      if (!signal.aborted) setError(cause instanceof Error ? cause.message : '데이터를 불러오지 못했습니다.')
    }).finally(() => {
      if (!signal.aborted) setLoading(false)
    })
    // A fast date/month switch must not display a late response for the previous date.
    return () => controller.abort()
  }, [date, month, restricted, revision, today])

  return { data, loading, error, restricted, refresh }
}
