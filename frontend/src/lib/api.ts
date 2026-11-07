import type { CalendarSummary, DailyStatistics, GrowthHistory, GrowthSummary, RetrospectiveKind, RetrospectiveList, Task, TaskInput, WeeklyStatistics } from '../types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error('서버에 연결하지 못했습니다. 백엔드 실행 상태를 확인해 주세요.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    throw new ApiError(response.status, typeof detail === 'string' ? detail :
      response.status === 422 ? '입력 내용을 확인해 주세요. 제목은 1~200자, 설명은 5,000자까지 입력할 수 있습니다.' :
      '요청을 처리하지 못했습니다. 다시 시도해 주세요.')
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

export const api = {
  tasks: (date: string, signal?: AbortSignal) => request<Task[]>(`/tasks?date=${date}`, { signal }),
  create: (data: TaskInput) => request<Task>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: number, data: Partial<TaskInput> & { is_completed?: boolean }) =>
    request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/tasks/${id}`, { method: 'DELETE' }),
  calendar: (month: string, signal?: AbortSignal) => {
    const [year, value] = month.split('-')
    return request<CalendarSummary>(`/calendar?year=${year}&month=${Number(value)}`, { signal })
  },
  daily: (date: string, signal?: AbortSignal) => request<DailyStatistics>(`/stats/daily?date=${date}`, { signal }),
  weekly: (signal?: AbortSignal) => request<WeeklyStatistics>('/stats/weekly', { signal }),
  retrospectives: (kind: RetrospectiveKind, date?: string, signal?: AbortSignal) =>
    request<RetrospectiveList>(`/retrospectives?kind=${kind}${date ? `&date=${date}` : ''}`, { signal }),
  growth: (signal?: AbortSignal) => request<GrowthSummary>('/growth/summary', { signal }),
  growthHistory: (offset = 0, signal?: AbortSignal) => request<GrowthHistory>(`/growth/history?limit=20&offset=${offset}`, { signal }),
}
