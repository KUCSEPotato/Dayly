import { useState } from 'react'
import { CalendarArrowUp, Tags } from 'lucide-react'
import { rateLabel } from '../lib/dates'
import { tagStyle } from '../lib/tags'
import type { AnalysisTag, RetrospectiveAnalysis as Analysis, TagActivity, TagPostponements } from '../types'

function AnalysisBadge({ tag }: { tag: AnalysisTag }) {
  return <span className="tag-chip" style={tagStyle(tag.color ?? '#8d9487')}>{tag.name}</span>
}

function leaders<T extends AnalysisTag>(rows: T[], value: (row: T) => number): string {
  const tagged = rows.filter(row => row.tag_id !== null)
  const best = Math.max(0, ...tagged.map(value))
  return best > 0 ? tagged.filter(row => value(row) === best).map(row => row.name).join(', ') : ''
}

export function RetrospectiveAnalysis({ analysis }: { analysis?: Analysis | null }) {
  const [allActivity, setAllActivity] = useState(false)
  const [allPostponements, setAllPostponements] = useState(false)
  if (!analysis) return <div className="panel analysis-legacy" role="note">이 회고는 상세 활동 분석 기능이 추가되기 전에 생성된 기록이에요.</div>
  const available = analysis.coverage.status === 'complete'
  const activity = analysis.tag_activity
  const postponements = analysis.postponements
  const mostCompleted = leaders<TagActivity>(activity, row => row.completed)
  const mostPlanned = leaders<TagActivity>(activity, row => row.total)
  const mostPostponed = leaders<TagPostponements>(postponements.by_tag, row => row.total_postponements)
  const unavailable = <div className="analysis-unavailable"><strong>{analysis.coverage.status === 'partial' ? '일부 기간만 기록되어 전체 분석을 제공하지 않아요.' : '이 기간은 태그·미루기 기록이 부족해 분석할 수 없어요.'}</strong>
    <p>미루기가 0회였다는 의미는 아니에요. 기록으로 확인할 수 있는 기간에만 수치를 표시해요.</p>
    {analysis.coverage.recording_started_at && <p>분석 기록 확인 시작: {new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(analysis.coverage.recording_started_at))} (서울)</p>}
  </div>

  return <div className="retrospective-analysis">
    <section className="panel analysis-panel" aria-labelledby="tag-analysis-title">
      <div className="section-heading"><div><span className="eyebrow">ACTIVITY BY TAG</span><h2 id="tag-analysis-title"><Tags size={17} />태그별 활동</h2></div></div>
      {!available ? unavailable : activity.length === 0 ? <p className="quiet-empty">이 기간에 예정된 할 일이 없어요.</p> : <>
        <div className="analysis-insights">{mostCompleted && <p>완료한 할 일이 가장 많은 태그: <strong>{mostCompleted}</strong></p>}{mostPlanned && <p>계획이 가장 많았던 태그: <strong>{mostPlanned}</strong></p>}</div>
        <ul className="tag-activity-list">{(allActivity ? activity : activity.slice(0, 6)).map(row => <li key={row.tag_id ?? 'untagged'}>
          <div className="analysis-row-heading"><AnalysisBadge tag={row} /><span>{row.completed} / {row.total}개 완료 · 미완료 {row.incomplete}개</span><strong>{rateLabel(row.completion_rate)}</strong></div>
          <div className="progress-track" role="progressbar" aria-label={`${row.name} 태그 달성률`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={row.completion_rate ?? 0} aria-valuetext={rateLabel(row.completion_rate)}><div className="progress-fill" style={{ width: `${row.completion_rate ?? 0}%`, backgroundColor: row.color ?? '#a1ad96' }} /></div>
        </li>)}</ul>
        {activity.length > 6 && <button className="text-button analysis-more" onClick={() => setAllActivity(value => !value)}>{allActivity ? '접기' : `태그 ${activity.length}개 모두 보기`}</button>}
      </>}
      <p className="analysis-footnote">날짜별 종료 상태를 기준으로 합산해요. 여러 태그가 붙은 할 일은 각 태그에 포함되어 태그별 합계와 전체 할 일 수가 다를 수 있어요. 같은 최댓값은 공동으로 표시해요.</p>
    </section>
    <section className="panel analysis-panel" aria-labelledby="postpone-analysis-title">
      <div className="section-heading"><div><span className="eyebrow">POSTPONEMENT RECORDS</span><h2 id="postpone-analysis-title"><CalendarArrowUp size={17} />미루기 현황</h2></div></div>
      {!available ? unavailable : <>
        <dl className="postponement-metrics"><div><dt>미룬 할 일</dt><dd>{postponements.postponed_tasks}<small>개</small></dd></div><div><dt>전체 미루기 횟수</dt><dd>{postponements.total_postponements}<small>회</small></dd></div><div><dt>누적 연기 일수</dt><dd>{postponements.postponed_days}<small>일</small></dd></div></dl>
        {postponements.total_postponements === 0 ? <p className="quiet-empty">이 기간에는 미루기 기록이 없어요.</p> : <>
          {mostPostponed && <p className="analysis-insight">미루기 기록이 가장 많은 태그: <strong>{mostPostponed}</strong></p>}
          <ul className="postponement-tag-list">{(allPostponements ? postponements.by_tag : postponements.by_tag.slice(0, 6)).map(row => <li key={row.tag_id ?? 'untagged'}><AnalysisBadge tag={row} /><span>할 일 {row.postponed_tasks}개 · {row.total_postponements}회 · {row.postponed_days}일</span></li>)}</ul>
          {postponements.by_tag.length > 6 && <button className="text-button analysis-more" onClick={() => setAllPostponements(value => !value)}>{allPostponements ? '접기' : `태그 ${postponements.by_tag.length}개 모두 보기`}</button>}
        </>}
      </>}
      <p className="analysis-footnote">미루기를 실행한 시각과 당시 태그를 기준으로 기록해요. 날짜 차이의 합은 최초 예정일 대비 최종 지연 기간과 달라요. 일반 날짜 수정은 포함하지 않아요.</p>
    </section>
  </div>
}
