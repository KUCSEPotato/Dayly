import { expect, test, type Page } from '@playwright/test'
import { addDays, seoulToday } from '../src/lib/dates'
import type { RetrospectiveList } from '../src/types'

const title = 'v023 · 날짜 지정'

async function create(page: Page) {
  const tag = await (await page.request.post('/api/tags', { data: { name: 'v023-Python', color: '#648ca6' } })).json() as { id: number }
  const response = await page.request.post('/api/tasks', { data: { title, description: '미뤄도 유지할 설명', scheduled_date: seoulToday(), tag_ids: [tag.id] } })
  expect(response.status()).toBe(201)
  return await response.json() as { id: number; tags: { id: number }[] }
}

test.afterEach(async ({ page }) => {
  for (let offset = 0; offset <= 4; offset++) {
    const response = await page.request.get(`/api/tasks?date=${addDays(seoulToday(), offset)}`)
    if (!response.ok()) continue
    const tasks: { id: number; title: string }[] = await response.json()
    for (const task of tasks) if (task.title === title) await page.request.delete(`/api/tasks/${task.id}`)
  }
})

test('custom postpone requires confirmation and moves three days with one request, preserving selection and tags', async ({ page }, testInfo) => {
  const original = await create(page)
  await page.goto('/')
  const trigger = page.getByRole('button', { name: title + ' 미루기', exact: true })
  await trigger.click()
  const popup = page.getByRole('dialog', { name: title + ' 미루기' })
  await expect(popup.getByRole('button', { name: '다음 날로 미루기', exact: true })).toBeVisible()
  await popup.getByRole('button', { name: '날짜 직접 지정' }).click()
  const input = popup.getByLabel('미룰 날짜')
  await expect(input).toHaveAttribute('min', addDays(seoulToday(), 1))
  const requests: unknown[] = []
  await page.route(`**/api/tasks/${original.id}/postpone`, async route => { requests.push(route.request().postDataJSON()); await route.continue() })
  await input.fill(seoulToday())
  await expect(popup.getByRole('button', { name: '미루기 확인' })).toBeDisabled()
  await input.fill(addDays(seoulToday(), -1))
  await expect(popup.getByRole('button', { name: '미루기 확인' })).toBeDisabled()
  const target = addDays(seoulToday(), 3)
  await input.fill(target)
  expect(requests).toEqual([])
  await expect(page.getByRole('checkbox', { name: title + ' 완료' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('postpone-date-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(popup).toBeVisible()
  const box = await popup.boundingBox()
  expect(box && box.x >= 0 && box.x + box.width <= 390 && box.y >= 0 && box.y + box.height <= 844).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('postpone-date-mobile.png'), fullPage: true })
  await popup.getByRole('button', { name: '미루기 확인' }).click()
  await expect(popup).not.toBeVisible()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  await expect(page.getByRole('group', { name: '날짜 선택' }).getByRole('button', { name: seoulToday(), exact: true })).toHaveAttribute('aria-pressed', 'true')
  expect(requests).toEqual([{ target_date: target }])
  const moved = await (await page.request.get(`/api/tasks?date=${target}`)).json() as { id: number; description: string; tags: { id: number }[] }[]
  expect(moved[0].id).toBe(original.id)
  expect(moved[0].tags).toEqual(original.tags)
  expect(moved[0].description).toBe('미뤄도 유지할 설명')
})

test('popover supports Escape/outside dismissal and a failed custom request preserves the selected date', async ({ page }) => {
  const original = await create(page)
  await page.goto('/')
  const trigger = page.getByRole('button', { name: title + ' 미루기', exact: true })
  const popup = page.getByRole('dialog', { name: title + ' 미루기' })
  await trigger.click()
  await expect(popup.getByRole('button', { name: '다음 날로 미루기', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(popup).not.toBeVisible()
  await expect(trigger).toBeFocused()
  await trigger.click()
  await page.getByRole('heading', { name: '나의 달력' }).click()
  await expect(popup).not.toBeVisible()
  await trigger.click()
  await popup.getByRole('button', { name: '날짜 직접 지정' }).click()
  const target = addDays(seoulToday(), 3)
  await popup.getByLabel('미룰 날짜').fill(target)
  await page.route(`**/api/tasks/${original.id}/postpone`, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '날짜 변경 실패' }) }))
  await popup.getByRole('button', { name: '미루기 확인' }).click()
  await expect(page.getByRole('alert')).toContainText('날짜 변경 실패')
  await expect(popup.getByLabel('미룰 날짜')).toHaveValue(target)
  await expect(page.getByRole('checkbox', { name: title + ' 완료' })).toBeVisible()
  await expect(popup.getByRole('button', { name: '미루기 확인' })).toBeEnabled()
})

test('weekly tag activity and all three postponement metrics are frozen, weighted and responsive', async ({ page }, testInfo) => {
  await page.goto('/#retrospectives/weekly')
  await expect(page.getByRole('button', { name: '이전 회고' })).toBeEnabled()
  await page.getByRole('button', { name: '이전 회고' }).click()
  const activity = page.getByRole('region', { name: '태그별 활동', exact: true })
  const postponed = page.getByRole('region', { name: '미루기 현황', exact: true })
  await expect(activity.getByRole('progressbar', { name: '회고 태그 태그 달성률' })).toHaveAttribute('aria-valuenow', '100')
  await expect(activity.getByRole('progressbar', { name: '태그 없음 태그 달성률' })).toHaveAttribute('aria-valuenow', '0')
  await expect(activity).toContainText('태그별 합계와 전체 할 일 수가 다를 수 있어요')
  await expect(postponed.locator('.postponement-metrics')).toHaveText('미룬 할 일1개전체 미루기 횟수2회누적 연기 일수5일')
  await expect(postponed.locator('.postponement-tag-list')).toContainText('할 일 1개 · 2회 · 5일')
  await expect(page.getByRole('progressbar', { name: '고정 회고 달성률' })).toHaveAttribute('aria-valuenow', '50')
  await page.screenshot({ path: testInfo.outputPath('analysis-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('analysis-mobile.png'), fullPage: true })
  await page.reload()
  await expect(page.getByRole('button', { name: '이전 회고' })).toBeEnabled()
  await page.getByRole('button', { name: '이전 회고' }).click()
  await expect(postponed.locator('.postponement-metrics')).toHaveText('미룬 할 일1개전체 미루기 횟수2회누적 연기 일수5일')
})

test('daily, weekly and monthly analyses match API availability; real zero differs from unknown history', async ({ page }) => {
  await page.goto('/#retrospectives/daily')
  for (const [kind, label] of [['daily', '일간'], ['weekly', '주간'], ['monthly', '월간']] as const) {
    await page.getByRole('tab', { name: label + ' 회고' }).click()
    const data = await (await page.request.get(`/api/retrospectives?kind=${kind}`)).json() as RetrospectiveList
    const record = data.items.find(item => item.period_start === data.requested_period?.start)!
    const section = page.getByRole('region', { name: '미루기 현황', exact: true })
    if (record.data.analysis?.coverage.status === 'complete') {
      await expect(section.locator('.postponement-metrics')).toBeVisible()
      await expect(section).toContainText('이 기간에는 미루기 기록이 없어요.')
    } else {
      await expect(section.locator('.postponement-metrics')).toHaveCount(0)
      await expect(section).toContainText('미루기가 0회였다는 의미는 아니에요.')
    }
  }
  await page.getByRole('tab', { name: '주간 회고' }).click()
  for (let i = 0; i < 7; i++) {
    await expect(page.getByRole('button', { name: '이전 회고' })).toBeEnabled()
    await page.getByRole('button', { name: '이전 회고' }).click()
  }
  await expect(page.getByRole('region', { name: '미루기 현황', exact: true })).toContainText('이 기간은 태그·미루기 기록이 부족해 분석할 수 없어요.')
  await expect(page.locator('.postponement-metrics')).toHaveCount(0)
})

test('legacy snapshot without analysis shows a compatibility notice instead of zeroes', async ({ page }) => {
  await page.route('**/api/retrospectives?**', async route => {
    const response = await route.fetch()
    const data = await response.json() as RetrospectiveList
    for (const item of data.items) delete item.data.analysis
    await route.fulfill({ response, json: data })
  })
  await page.goto('/#retrospectives/daily')
  await expect(page.getByRole('note')).toHaveText('이 회고는 상세 활동 분석 기능이 추가되기 전에 생성된 기록이에요.')
  await expect(page.locator('.postponement-metrics')).toHaveCount(0)
  await expect(page.getByRole('progressbar', { name: '고정 회고 달성률' })).toBeVisible()
})
