import { expect, test, type Page } from '@playwright/test'
import { addDays, formatDay, seoulToday } from '../src/lib/dates'

const prefix = 'v022 · '

async function createTask(page: Page, title: string, scheduled_date = seoulToday(), tag_ids: number[] = []) {
  const response = await page.request.post('/api/tasks', { data: { title: prefix + title, scheduled_date, tag_ids } })
  expect(response.status()).toBe(201)
  return await response.json() as { id: number; title: string; tags: { id: number; name: string; color: string }[] }
}
async function selectDay(page: Page, day: string) {
  const button = page.getByRole('group', { name: '날짜 선택' }).getByRole('button', { name: new RegExp(`^${day}`) })
  if (!await button.count()) await page.getByRole('button', { name: '다음 달', exact: true }).click()
  await button.click()
}

test.afterEach(async ({ page }) => {
  for (let offset = 0; offset < 5; offset++) {
    const response = await page.request.get(`/api/tasks?date=${addDays(seoulToday(), offset)}`)
    if (!response.ok()) continue
    const tasks: { id: number; title: string }[] = await response.json()
    for (const task of tasks) if (task.title.startsWith(prefix)) await page.request.delete(`/api/tasks/${task.id}`)
  }
})

test('tags: create with palette, assign multiple, search, reuse, remove, reload and mobile', async ({ page }, testInfo) => {
  await page.goto('/')
  await page.getByRole('button', { name: '할 일 추가', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('할 일 제목').fill(prefix + '태그 UI')
  const search = dialog.getByLabel('태그 검색 또는 새 이름')
  await search.fill('v022-Python')
  await dialog.getByRole('radio', { name: '파랑', exact: true }).check()
  await dialog.getByRole('button', { name: '“v022-Python” 태그 만들기' }).click()
  await expect(dialog.getByRole('button', { name: 'v022-Python 태그 지정 해제' })).toBeVisible()
  await search.fill('v022-Dayly')
  await dialog.getByRole('button', { name: '“v022-Dayly” 태그 만들기' }).click()
  await expect(dialog.getByRole('button', { name: 'v022-Dayly 태그 지정 해제' })).toBeVisible()
  await dialog.getByRole('button', { name: '할 일 추가', exact: true }).click()
  const row = page.locator('.task-item').filter({ hasText: prefix + '태그 UI' })
  await expect(row.getByLabel('지정된 태그')).toHaveText('v022-Pythonv022-Dayly')
  await page.reload()
  await expect(row.getByLabel('지정된 태그')).toContainText('v022-Python')
  await row.getByRole('button', { name: prefix + '태그 UI 수정' }).click()
  await dialog.getByRole('button', { name: 'v022-Dayly 태그 지정 해제' }).click()
  await search.fill('PYTH')
  await expect(dialog.getByLabel('기존 태그').getByRole('button', { name: 'v022-Python', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await dialog.getByRole('button', { name: '변경 저장' }).click()
  await expect(row.getByLabel('지정된 태그')).toHaveText('v022-Python')
  const tags = await (await page.request.get('/api/tags?q=v022-Python')).json() as { id: number; color: string }[]
  expect(tags).toHaveLength(1)
  expect(tags[0].color).toBe('#648ca6')
  const reused = await createTask(page, '재사용', seoulToday(), [tags[0].id])
  expect(reused.tags[0].id).toBe(tags[0].id)
  await page.reload()
  await page.getByRole('checkbox', { name: prefix + '태그 UI 완료' }).click()
  await expect(row.getByRole('button', { name: prefix + '태그 UI 다음 날로 미루기' })).toBeDisabled()
  await expect(row.getByLabel('지정된 태그')).toHaveText('v022-Python')
  await page.screenshot({ path: testInfo.outputPath('tags-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await row.getByRole('button', { name: prefix + '태그 UI 수정' }).click()
  await search.fill('아주긴태그이름으로모바일줄바꿈을확인해요12345')
  await dialog.getByRole('button', { name: /태그 만들기/ }).click()
  await expect(dialog.getByLabel('선택한 태그')).toContainText('아주긴태그')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('tags-mobile-dialog.png'), fullPage: true })
  await dialog.getByRole('button', { name: '변경 저장' }).click()
  await expect(dialog).not.toBeVisible()
  expect(await row.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('tags-mobile-list.png'), fullPage: true })
})

test('postpone updates calendar and daily/weekly progress without changing selection or reloading', async ({ page }) => {
  const today = seoulToday(), tomorrow = addDays(today, 1)
  const complete = await createTask(page, '완료 유지')
  await page.request.patch(`/api/tasks/${complete.id}`, { data: { is_completed: true } })
  const pending = await createTask(page, '미루기')
  await page.goto('/')
  const summary = page.getByRole('region', { name: '달성률 요약' })
  await summary.getByRole('button', { name: '오늘', exact: true }).click()
  await expect(summary.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50')
  const navigations: string[] = []
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations.push(frame.url()) })
  const postpone = page.getByRole('button', { name: pending.title + ' 다음 날로 미루기' })
  await expect(postpone).toHaveAttribute('title', '다음 날로 미루기')
  await postpone.click()
  await expect(page.getByRole('status').filter({ hasText: '로 할 일을 미뤘어요.' })).toHaveText(`${formatDay(tomorrow, { month: 'long', day: 'numeric' })}로 할 일을 미뤘어요.`)
  await expect(page.getByRole('checkbox', { name: pending.title + ' 완료' })).toHaveCount(0)
  await expect(summary.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  await summary.getByRole('button', { name: '최근 7일', exact: true }).click()
  await expect(summary.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  const calendar = page.getByRole('group', { name: '날짜 선택' })
  await expect(calendar.getByRole('button', { name: new RegExp(`^${today}, 1개 중 1개 완료`) })).toHaveAttribute('aria-pressed', 'true')
  await selectDay(page, tomorrow)
  await expect(page.getByRole('checkbox', { name: pending.title + ' 완료' })).toBeVisible()
  await expect(page.getByRole('progressbar', { name: '선택한 날짜 달성률' })).toHaveAttribute('aria-valuenow', '0')
  const moved = await (await page.request.get(`/api/tasks?date=${tomorrow}`)).json() as { id: number }[]
  expect(moved.map(task => task.id)).toContain(pending.id)
  expect(navigations).toEqual([])
})

test('future task moves from its scheduled date and supports consecutive postponements', async ({ page }) => {
  const future = addDays(seoulToday(), 1)
  const pending = await createTask(page, '미래 일정', future)
  await page.goto('/')
  await selectDay(page, future)
  await page.getByRole('button', { name: pending.title + ' 다음 날로 미루기' }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  await expect(page.getByRole('group', { name: '날짜 선택' }).getByRole('button', { name: future, exact: true })).toHaveAttribute('aria-pressed', 'true')
  await selectDay(page, addDays(future, 1))
  await page.getByRole('button', { name: pending.title + ' 다음 날로 미루기' }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  expect((await (await page.request.get(`/api/tasks?date=${addDays(future, 2)}`)).json())[0].id).toBe(pending.id)
})

test('failed postpone preserves task and retry disables duplicate clicks until request finishes', async ({ page }) => {
  const pending = await createTask(page, '실패 후 재시도')
  await page.goto('/')
  const button = page.getByRole('button', { name: pending.title + ' 다음 날로 미루기' })
  const path = `**/api/tasks/${pending.id}/postpone`
  await page.route(path, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '미루기 실패' }) }))
  await button.click()
  await expect(page.getByRole('alert')).toContainText('미루기 실패')
  await expect(page.getByRole('checkbox', { name: pending.title + ' 완료' })).toBeVisible()
  await expect(page.getByText(/로 할 일을 미뤘어요/)).toHaveCount(0)
  await page.unroute(path)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let requests = 0
  await page.route(path, async route => { requests++; await gate; await route.continue() })
  await button.click()
  try {
    await expect(button).toBeDisabled()
    await button.evaluate(element => { (element as HTMLButtonElement).click(); (element as HTMLButtonElement).click() })
    expect(requests).toBe(1)
  } finally { release() }
  await expect(page.getByRole('checkbox', { name: pending.title + ' 완료' })).toHaveCount(0)
  expect((await (await page.request.get(`/api/tasks?date=${addDays(seoulToday(), 1)}`)).json())[0].id).toBe(pending.id)
})

test('tag creation failure keeps form and existing task fields intact', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '할 일 추가', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('할 일 제목').fill(prefix + '입력 보존')
  await dialog.getByLabel('태그 검색 또는 새 이름').fill('v022-failure')
  await page.route('**/api/tags', route => route.request().method() === 'POST' ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '태그 저장 실패' }) }) : route.continue())
  await dialog.getByRole('button', { name: '“v022-failure” 태그 만들기' }).click()
  await expect(dialog.getByRole('alert')).toContainText('태그 저장 실패')
  await expect(dialog.getByLabel('할 일 제목')).toHaveValue(prefix + '입력 보존')
  await expect(dialog.getByLabel('태그 검색 또는 새 이름')).toHaveValue('v022-failure')
  await expect(dialog.getByRole('button', { name: '할 일 추가', exact: true })).toBeEnabled()
  await dialog.getByRole('button', { name: '취소', exact: true }).click()
})
