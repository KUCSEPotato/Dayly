export interface Tag { id: number; name: string; color: string }

export interface Task {
  id: number
  title: string
  description: string | null
  scheduled_date: string
  is_completed: boolean
  created_at: string
  updated_at: string
  completed_at: string | null
  tags?: Tag[] // Snapshots written before v0.2.2 have no tags field.
}

export interface TaskInput {
  title: string
  description: string | null
  scheduled_date: string
  tag_ids?: number[]
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

export type RetrospectiveKind = 'daily' | 'weekly' | 'monthly'
export interface RetrospectiveDay extends Omit<DailyStatistics, 'total' | 'completed' | 'incomplete'> {
  total: number | null
  completed: number | null
  incomplete: number | null
  coverage: 'complete' | 'partial' | 'unavailable'
}
export interface AnalysisTag { tag_id: number | null; name: string; color: string | null }
export interface TagActivity extends AnalysisTag {
  total: number; completed: number; incomplete: number; completion_rate: number | null
}
export interface TagPostponements extends AnalysisTag {
  postponed_tasks: number; total_postponements: number; postponed_days: number
}
export interface RetrospectiveAnalysis {
  version: 'v0.2.3'
  coverage: { status: 'complete' | 'partial' | 'unavailable'; recording_started_at: string | null }
  tag_activity: TagActivity[]
  postponements: {
    postponed_tasks: number | null; total_postponements: number | null; postponed_days: number | null
    by_tag: TagPostponements[]
  }
}
export interface Retrospective {
  id: number
  kind: RetrospectiveKind
  period_start: string
  period_end: string
  created_at: string
  status: 'ready' | 'no_activity' | 'partial' | 'unavailable'
  total: number | null
  completed: number | null
  incomplete: number | null
  completion_rate: number | null
  xp_total: number
  data: {
    completed_tasks: Task[]
    incomplete_tasks: Task[]
    days: RetrospectiveDay[]
    weeks: { start: string; end: string; completed: number; total: number; completion_rate: number | null }[]
    best_day: string | null
    best_week: string | null
    activity: { unique_completed_tasks: number; task_ids: number[] }
    recording_started_at: string
    xp_policy: Record<string, unknown>
    analysis?: RetrospectiveAnalysis | null
  }
}
export interface RetrospectiveList {
  items: Retrospective[]
  total: number
  requested_period: { kind: RetrospectiveKind; start: string; end: string } | null
  status: Retrospective['status'] | 'not_ended' | null
}
export interface GrowthSummary {
  total_xp: number
  level: number
  xp_into_level: number
  next_level_xp: number
  xp_to_next_level: number
  policy: { task_points: number; daily_cap: number; bonus_half: number; bonus_full: number; level_step: number }
}
export interface ExperienceGrant {
  id: number
  reason: string
  task_id: number | null
  event_id: number | null
  amount: number
  earned_date: string
  occurred_at: string
  created_at: string
  policy_version: string
}
export interface GrowthHistory { items: ExperienceGrant[]; total: number }
