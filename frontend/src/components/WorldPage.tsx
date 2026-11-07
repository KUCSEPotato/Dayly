import { useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, LoaderCircle, Sparkles, TreePine, Waves } from 'lucide-react'
import { api } from '../lib/api'
import { formatDay } from '../lib/dates'
import type { GrowthHistory, GrowthSummary } from '../types'

export function WorldPage() {
  const [summary, setSummary] = useState<GrowthSummary | null>(null)
  const [history, setHistory] = useState<GrowthHistory | null>(null)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(null)
    Promise.all([api.growth(controller.signal), api.growthHistory(offset, controller.signal)]).then(([growth, grants]) => {
      if (!controller.signal.aborted) { setSummary(growth); setHistory(grants) }
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '성장 기록을 불러오지 못했습니다.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [offset, revision])
  return <div className="world-page"><section className="feature-intro"><span className="eyebrow">A WORLD GROWING WITH YOU</span><h1>나만의 세계<span>.</span></h1><p>하나씩 해낸 일이 경험치로 쌓이고 있어요. 나의 작은 세계를 위한 준비입니다.</p></section>
    {error && <div className="error-banner" role="alert"><p>{error}</p><button className="button button-quiet" onClick={() => setRevision(value => value + 1)}>다시 시도</button></div>}
    {loading ? <div className="panel statistics-loading" role="status"><LoaderCircle className="spin" size={18} />성장 기록을 불러오는 중이에요.</div> : !error && summary && <>
      <section className="panel growth-overview" aria-label="성장 상태"><div className="growth-level"><Sparkles size={24} /><span>현재 성장 레벨</span><strong>Lv. {summary.level}</strong></div>
        <div className="growth-progress"><span>누적 경험치 <strong>{summary.total_xp} XP</strong></span><div className="progress-track" role="progressbar" aria-label="다음 레벨 진행률" aria-valuemin={0} aria-valuemax={summary.next_level_xp} aria-valuenow={summary.xp_into_level}><div className="progress-fill" style={{ width: `${summary.xp_into_level / summary.next_level_xp * 100}%` }} /></div><p>다음 레벨까지 {summary.xp_to_next_level} XP</p></div>
      </section>
      <section className="world-coming"><span className="coming-tag">COMING SOON · v1.0</span><h2>어떤 세계를 가꾸게 될까요?</h2><p>지금 쌓는 경험치가 두 테마에 공통으로 이어집니다.</p><div className="theme-grid">
        <article className="panel theme-card forest"><TreePine size={45} strokeWidth={1.2} /><span>FOREST</span><h3>작은 숲의 시작</h3><p>매일의 실천으로 천천히 자라날<br />나무와 초록빛 풍경을 준비하고 있어요.</p></article>
        <article className="panel theme-card ocean"><Waves size={45} strokeWidth={1.2} /><span>OCEAN</span><h3>잔잔한 바다의 시작</h3><p>나만의 속도로 넓어질 바다와<br />함께할 고래의 이야기를 준비하고 있어요.</p></article>
      </div></section>
      <p className="xp-policy-note">임시 경험치 정책: 최초 완료 {summary.policy.task_points} XP · 하루 최대 {summary.policy.daily_cap} XP · 확정 달성률 50% 이상 +{summary.policy.bonus_half} / 100% +{summary.policy.bonus_full} XP. 완료 해제·삭제 시 회수하지 않으며 같은 할 일의 반복 완료에는 다시 지급하지 않아요.</p>
      <section className="panel xp-history"><div className="section-heading"><h2>경험치 획득 내역</h2><span>{history?.total ?? 0}건</span></div>
        {history?.items.length ? <ul>{history.items.map(grant => <li key={grant.id}><div><strong>{grant.reason === 'DAILY_BONUS' ? '확정 달성률 보너스' : '할 일 최초 완료'}</strong><span>{formatDay(grant.earned_date, { year: 'numeric', month: 'long', day: 'numeric' })}{grant.amount === 0 ? ' · 일일 상한 적용' : ''}</span></div><strong>+{grant.amount} XP</strong></li>)}</ul> : <p className="quiet-empty">아직 획득한 경험치가 없어요. 할 일 하나를 완료하며 시작해 보세요.</p>}
        {history && history.total > 20 && <div className="history-pagination"><button className="button button-quiet" disabled={offset === 0} onClick={() => setOffset(value => value - 20)}><ArrowLeft size={14} />이전</button><button className="button button-quiet" disabled={offset + 20 >= history.total} onClick={() => setOffset(value => value + 20)}>다음<ArrowRight size={14} /></button></div>}
      </section>
    </>}
  </div>
}
