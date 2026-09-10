import { expect, type Page, test } from '@playwright/test'

const password = 'correct horse battery staple'
let locationsPath = ''

async function login(page: Page, username: string): Promise<void> {
  await page.context().clearCookies()
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByLabel('Open application menu')).toBeVisible()
}

async function createRoot(page: Page, name: string, type = 'room'): Promise<void> {
  await page.getByRole('button', { name: 'Add root location' }).click()
  const form = page.locator('form').filter({ hasText: 'Add root location' })
  await form.getByLabel('Name').fill(name)
  await form.getByLabel('Type').selectOption(type)
  await form.getByRole('button', { name: 'Add location' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: name }).first()).toBeVisible()
}

async function createChild(page: Page, parent: string, name: string, type = 'room'): Promise<void> {
  await page.getByRole('button', { name: `Add child to ${parent}` }).click()
  const form = page.locator('form').filter({ hasText: `Add child to ${parent}` })
  await form.getByLabel('Name').fill(name)
  await form.getByLabel('Type').selectOption(type)
  await form.getByRole('button', { name: 'Add child' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: name }).last()).toBeVisible()
}

test.describe.serial('T05 location tree', () => {
  test('collection owner creates, edits, reparents, roots, and deletes locations', async ({ page }) => {
    await login(page, 'adminuser')
    await page.goto('/collections')
    await page.getByRole('link', { name: 'Browser collection' }).click()
    await page.getByRole('link', { name: 'Locations' }).click()
    locationsPath = new URL(page.url()).pathname
    await expect(page.getByRole('heading', { name: 'No locations yet' })).toBeVisible()

    await createRoot(page, 'House')
    await createChild(page, 'House', 'Basement')
    await createChild(page, 'Basement', 'Shelf', 'shelf')
    await createChild(page, 'Shelf', 'Box', 'box')
    await createRoot(page, 'Garage')
    await createChild(page, 'Garage', 'Cabinet', 'cabinet')
    await expect(page.getByRole('listitem').filter({ hasText: 'House' }).first()).toContainText('Basement')
    await expect(page.getByRole('listitem').filter({ hasText: 'Shelf' }).first()).toContainText('Box')

    await page.getByRole('button', { name: 'Edit Box' }).click()
    const editForm = page.locator('form').filter({ hasText: 'Edit Box' })
    await editForm.getByLabel('Name').fill('Archive Box')
    await editForm.getByLabel('Parent').selectOption({ label: 'Garage / Cabinet' })
    await editForm.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByRole('listitem').filter({ hasText: 'Cabinet' }).first()).toContainText('Archive Box')
    await expect(page.getByRole('listitem').filter({ hasText: 'Shelf' }).first()).not.toContainText('Archive Box')

    await page.getByRole('button', { name: 'Edit Archive Box' }).click()
    const moveToRoot = page.locator('form').filter({ hasText: 'Edit Archive Box' })
    await moveToRoot.getByLabel('Parent').selectOption({ label: 'No parent / Root' })
    await moveToRoot.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByRole('list', { name: 'Location tree' }).locator(':scope > li').filter({ hasText: 'Archive Box' })).toBeVisible()

    await page.getByRole('button', { name: 'Edit House' }).click()
    const houseForm = page.locator('form').filter({ hasText: 'Edit House' })
    const parentChoices = await houseForm.getByLabel('Parent').locator('option').allTextContents()
    expect(parentChoices).toContain('No parent / Root')
    expect(parentChoices).toContain('Garage')
    expect(parentChoices).not.toContain('House')
    expect(parentChoices).not.toContain('House / Basement')
    expect(parentChoices).not.toContain('House / Basement / Shelf')
    await houseForm.getByRole('button', { name: 'Cancel' }).click()

    await createRoot(page, 'Temporary box', 'box')
    await page.getByRole('button', { name: 'Delete Temporary box' }).click()
    await expect(page.getByRole('heading', { name: 'Delete Temporary box?' })).toBeVisible()
    await page.getByRole('button', { name: 'Confirm delete' }).click()
    await expect(page.getByText('Temporary box')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Delete House' })).toBeDisabled()
    await expect(page.getByText('Move or remove child locations before deleting.').first()).toBeVisible()
  })

  test('editor can mutate locations while viewer remains read-only', async ({ page }) => {
    await login(page, 'editoruser')
    await page.goto(locationsPath)
    await expect(page.getByRole('heading', { name: 'Locations' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Add root location' })).toBeVisible()
    await createRoot(page, 'Editor shelf', 'shelf')
    await expect(page.getByRole('button', { name: 'Edit Editor shelf' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete Editor shelf' })).toBeVisible()

    await login(page, 'vieweruser')
    await page.goto(locationsPath)
    await expect(page.getByRole('heading', { name: 'Locations' })).toBeVisible()
    await expect(page.getByText('House')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Add root location' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Add child to/ })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Edit / })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Delete / })).toHaveCount(0)
  })

  test('outsider and instance admin without membership cannot read locations', async ({ page }) => {
    await login(page, 'outsideruser')
    await page.goto('/collections')
    await expect(page.getByText('Browser collection')).toHaveCount(0)
    await page.goto(locationsPath)
    await expect(page.getByRole('heading', { name: 'Locations unavailable' })).toBeVisible()
    await expect(page.getByText('House')).toHaveCount(0)

    await login(page, 'secondinstanceadmin')
    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: 'Local users' })).toBeVisible()
    await page.goto(locationsPath)
    await expect(page.getByRole('heading', { name: 'Locations unavailable' })).toBeVisible()
    await expect(page.getByText('House')).toHaveCount(0)
  })
})
