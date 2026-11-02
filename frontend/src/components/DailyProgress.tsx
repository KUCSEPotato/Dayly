import { rateLabel } from '../lib/dates'
import type { DailyStatistics } from '../types'

export function DailyProgress({ stats }: { stats: DailyStatistics }) {
  return <div className="daily-progress">
    <div className="flex items-center justify-between gap-3">
      <span>하루 달성률 <span className="progress-count">{stats.completed} / {stats.total}</span></span>
      <strong>{rateLabel(stats.completion_rate)}</strong>
    </div>
    <div className="progress-track" role="progressbar" aria-label="선택한 날짜 달성률" aria-valuemin={0} aria-valuemax={100}
      aria-valuenow={stats.completion_rate ?? 0} aria-valuetext={rateLabel(stats.completion_rate)}>
      <div className="progress-fill" style={{ width: `${stats.completion_rate ?? 0}%` }} />
    </div>
  </div>
}
