export interface Task {
  id: number
  title: string
  description: string | null
  scheduled_date: string
  is_completed: boolean
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface TaskInput {
  title: string
  description: string | null
  scheduled_date: string
}

export interface DailyStatistics {
  date: string
  total: number
  completed: number
  incomplete: number
  completion_rate: number | null
}

export interface WeeklyStatistics {
  start_date: string
  end_date: string
  total: number
  completed: number
  incomplete: number
  completion_rate: number | null
  days: DailyStatistics[]
}

export interface CalendarSummary {
  year: number
  month: number
  days: DailyStatistics[]
}
