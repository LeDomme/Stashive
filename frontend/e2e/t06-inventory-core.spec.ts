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
  await page.getByRole('button', { name: 'Add physical copy' }).click()
  await page.getByLabel('Edition').selectOption({ label: 'T06 Browser Title — T06 Browser Edition' })
  await page.getByRole('button', { name: 'Create physical copy' }).click()
  await page.getByRole('button', { name: 'Add physical copy' }).click()
  await page.getByLabel('Edition').selectOption({ label: 'T06 Browser Title — T06 Browser Edition' })
  await page.getByRole('button', { name: 'Create physical copy' }).click()
  await expect(page.getByText('T06 Browser Title')).toHaveCount(2)
  await expect(page.getByText('Unassigned', { exact: true })).toHaveCount(2)

  const firstCopy = page.locator('.inventory-list > li').filter({ hasText: 'T06 Browser Title' }).first()
  await firstCopy.getByRole('button', { name: 'Assign location' }).click()
  await firstCopy.getByLabel('Location').selectOption({ index: 1 })
  await firstCopy.getByRole('button', { name: 'Save location' }).click()
  await expect(firstCopy.getByText('Unassigned', { exact: true })).toHaveCount(0)
  await firstCopy.getByRole('button', { name: 'Remove location' }).click()
  await firstCopy.getByRole('button', { name: 'Save location' }).click()
  await expect(firstCopy.getByText('Unassigned', { exact: true })).toBeVisible()
})
