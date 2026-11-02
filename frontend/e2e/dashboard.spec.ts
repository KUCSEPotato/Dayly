import { expect, test } from '@playwright/test'
import { seoulToday } from '../src/lib/dates'

test('real API: create, complete, persist, edit, reschedule, and delete', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  await page.getByRole('button', { name: '할 일 추가', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('할 일 제목').fill('FastAPI 계층 학습')
  await dialog.getByLabel('상세 설명').fill('Router → Service → Model')
  const today = await dialog.getByLabel('예정 날짜').inputValue()
  await dialog.getByRole('button', { name: '할 일 추가', exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await expect(page.getByText('Router → Service → Model')).toBeVisible()
  await page.getByRole('checkbox', { name: 'FastAPI 계층 학습 완료' }).click()
  await expect(page.getByRole('checkbox', { name: 'FastAPI 계층 학습 완료' })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  await page.reload()
  await expect(page.getByRole('checkbox', { name: 'FastAPI 계층 학습 완료' })).toHaveAttribute('aria-checked', 'true')
  await page.getByRole('checkbox', { name: 'FastAPI 계층 학습 완료' }).click()
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0')
  await page.getByRole('button', { name: 'FastAPI 계층 학습 수정' }).click()
  await dialog.getByLabel('할 일 제목').fill('SQLAlchemy 실습')
  await dialog.getByRole('button', { name: '변경 저장' }).click()
  await expect(page.getByText('SQLAlchemy 실습', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'SQLAlchemy 실습 수정' }).click()
  const next = new Date(`${today}T00:00:00Z`)
  next.setUTCDate(next.getUTCDate() + 1)
  const tomorrow = next.toISOString().slice(0, 10)
  await dialog.getByLabel('예정 날짜').fill(tomorrow)
  await dialog.getByRole('button', { name: '변경 저장' }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  // A future task is reachable through the real calendar without a page reload.
  const tomorrowButton = page.getByRole('button', { name: new RegExp(`^${tomorrow}`) })
  await tomorrowButton.click()
  await expect(page.getByText('SQLAlchemy 실습', { exact: true })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByText('SQLAlchemy 실습', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true })
  await page.getByRole('button', { name: 'SQLAlchemy 실습 삭제' }).click()
  await page.getByRole('button', { name: '삭제', exact: true }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
})

test('failed write keeps form input and displays an error', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '할 일 추가', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('할 일 제목').fill('실패 시 유지되는 입력')
  await page.route('**/api/tasks', route => route.request().method() === 'POST'
    ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '테스트 저장 오류' }) })
    : route.continue())
  await dialog.getByRole('button', { name: '할 일 추가', exact: true }).click()
  await expect(dialog.getByRole('alert')).toHaveText('테스트 저장 오류')
  await expect(dialog.getByLabel('할 일 제목')).toHaveValue('실패 시 유지되는 입력')
  await expect(dialog).toBeVisible()
})

test('month navigation, old history restriction, and request failure recovery', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  await page.getByRole('button', { name: '이전 달', exact: true }).click()
  await page.getByRole('group', { name: '날짜 선택' }).getByRole('button').nth(10).click()
  await expect(page.getByRole('heading', { name: '지난 기록은 달력에 남아 있어요' })).toBeVisible()
  await expect(page.getByRole('button', { name: '할 일 추가', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: '오늘로' }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
  await page.route('**/api/stats/weekly', route => route.abort())
  await page.reload()
  await expect(page.getByRole('alert')).toContainText('기록을 불러오지 못했어요.')
  await page.unroute('**/api/stats/weekly')
  await page.getByRole('button', { name: '다시 시도' }).click()
  await expect(page.getByRole('heading', { name: '아직 비어 있는 하루' })).toBeVisible()
})

test('70% daily and weekly charts reflect real tasks, failed completion preserves state', async ({ page }, testInfo) => {
  const ids: number[] = []
  try {
    for (let index = 0; index < 10; index++) {
      const response = await page.request.post('/api/tasks', {
        data: { title: `통계 확인 ${index + 1}`, scheduled_date: seoulToday() },
      })
      expect(response.status()).toBe(201)
      const task: { id: number } = await response.json()
      ids.push(task.id)
      if (index < 7) {
        const completed = await page.request.patch(`/api/tasks/${task.id}`, { data: { is_completed: true } })
        expect(completed.ok()).toBe(true)
      }
    }
    await page.goto('/')
    await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '70')
    await expect(page.locator('.weekly-rate')).toHaveText('70%')
    await expect(page.getByRole('button', { name: new RegExp(`^${seoulToday()}, 7/10개 완료, 70%`) })).toBeVisible()
    await page.route(`**/api/tasks/${ids[7]}`, route => route.fulfill({
      status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '완료 저장 실패' }),
    }))
    await page.getByRole('checkbox', { name: '통계 확인 8 완료', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('완료 저장 실패')
    await expect(page.getByRole('checkbox', { name: '통계 확인 8 완료', exact: true })).toHaveAttribute('aria-checked', 'false')
    await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '70')
    await page.screenshot({ path: testInfo.outputPath('statistics-desktop.png'), fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath('statistics-mobile.png'), fullPage: true })
  } finally {
    for (const id of ids) await page.request.delete(`/api/tasks/${id}`)
  }
})
