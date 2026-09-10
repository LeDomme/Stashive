import { expect, test } from '@playwright/test'

const password = 'correct horse battery staple'

test('generic inventory workflow supports duplicate copies and location states', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('adminuser')
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByLabel('Open application menu')).toBeVisible()
  await page.goto('/collections')
  await page.getByRole('link', { name: 'Browser collection' }).click()
  const collectionPath = new URL(page.url()).pathname
  const collectionId = collectionPath.split('/').at(-2)

  await page.goto(`/collections/${collectionId}/catalog`)
  await page.getByRole('button', { name: 'New catalog entry' }).click()
  await page.getByLabel('Display title').fill('T06 Browser Title')
  await page.getByLabel('Type').fill('movie')
  await page.getByRole('button', { name: 'Create entry' }).click()
  await page.getByLabel('Edition name').fill('T06 Browser Edition')
  await page.getByRole('button', { name: 'Add edition' }).click()
  await page.getByRole('button', { name: 'Add identifier' }).click()
  await page.getByLabel('Identifier type').fill('EAN')
  await page.getByLabel('Identifier value').fill('1234567890123')
  await page.getByRole('button', { name: 'Create identifier' }).click()

  await page.goto(`/collections/${collectionId}/inventory`)
  await page.getByRole('button', { name: 'Add item' }).click()
  await page.getByLabel('Edition').selectOption({ label: 'T06 Browser Title — T06 Browser Edition' })
  await page.getByRole('button', { name: 'Create physical copy' }).click()
  await page.getByRole('button', { name: 'Add item' }).click()
  await page.getByLabel('Edition').selectOption({ label: 'T06 Browser Title — T06 Browser Edition' })
  await page.getByRole('button', { name: 'Create physical copy' }).click()
  const titleCard = page.locator('.library-card').filter({ hasText: 'T06 Browser Title' })
  await expect(titleCard).toHaveCount(1)
  await expect(titleCard).toContainText('1 edition · 2 copies')
  await expect(page.locator('.filter-toolbar__summary')).toContainText('1 title · 2 physical copies')
})
