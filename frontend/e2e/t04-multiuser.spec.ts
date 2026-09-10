import { expect, type Page, test } from '@playwright/test'

const password = 'correct horse battery staple'
let collectionPath = ''

async function login(
  page: Page,
  username: string,
  userPassword = password,
  expectSuccess = true,
): Promise<void> {
  await page.context().clearCookies()
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(userPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  if (expectSuccess) await expect(page.getByLabel('Open application menu')).toBeVisible()
}

async function createUser(page: Page, username: string, isInstanceAdmin = false): Promise<void> {
  const form = page.locator('form').filter({ hasText: 'Create local user' })
  await form.getByLabel('Username').fill(username)
  await form.getByLabel('Initial password').fill(password)
  if (isInstanceAdmin) await form.getByLabel('Make this user an instance admin').check()
  await form.getByRole('button', { name: 'Create user' }).click()
  await expect(page.getByRole('list', { name: 'Local users' }).getByText(`(${username})`)).toBeVisible()
}

async function addMember(page: Page, username: string, role: 'admin' | 'editor' | 'viewer'): Promise<void> {
  const form = page.locator('form').filter({ hasText: 'Add a member' })
  await form.getByLabel('Exact username').fill(username)
  await form.getByLabel('Role').selectOption(role)
  await form.getByRole('button', { name: 'Add member' }).click()
  await expect(page.getByRole('list', { name: 'Collection members' }).getByText(`(${username})`)).toBeVisible()
}

test.describe.serial('T04 multiuser collection access', () => {
  test('bootstraps the first instance admin and creates local test users', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Create the first administrator.' })).toBeVisible()
    await page.getByLabel('Setup token').fill('e2e-setup-token')
    await page.getByLabel('Username').fill('ownerUser')
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Create administrator' }).click()
    await expect(page.getByLabel('Open application menu')).toBeVisible()
    await page.goto('/setup')
    await expect(page.getByRole('heading', { name: 'Stashive is ready to grow.' })).toBeVisible()

    await page.getByLabel('Open application menu').click()
    await page.getByRole('link', { name: 'Administration' }).click()
    await createUser(page, 'adminUser')
    await createUser(page, 'editorUser')
    await createUser(page, 'viewerUser')
    await createUser(page, 'outsiderUser')
    await createUser(page, 'secondInstanceAdmin', true)
  })

  test('owner creates, shares, and manages a collection', async ({ page }) => {
    await login(page, 'owneruser')
    await page.goto('/collections')
    const form = page.locator('form').filter({ hasText: 'Create a collection' })
    await form.getByLabel('Name').fill('Browser collection')
    await form.getByRole('button', { name: 'Create collection' }).click()
    await expect(page.getByRole('heading', { name: 'Browser collection' })).toBeVisible()
    collectionPath = new URL(page.url()).pathname

    await expect(page.getByRole('button', { name: 'Edit details' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete collection' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Members' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Transfer ownership' })).toBeVisible()
    await addMember(page, 'adminuser', 'admin')
    await addMember(page, 'editoruser', 'editor')
    await addMember(page, 'vieweruser', 'viewer')
    const viewerRow = page.getByRole('listitem').filter({ hasText: '(vieweruser)' })
    await viewerRow.getByLabel('Role').selectOption('editor')
    await expect(viewerRow.getByLabel('Role')).toHaveValue('editor')
  })

  test('admin can manage members but cannot delete or transfer ownership', async ({ page }) => {
    await login(page, 'adminuser')
    await page.goto(collectionPath)
    await expect(page.getByRole('heading', { name: 'Browser collection' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Edit details' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete collection' })).toHaveCount(0)
    await expect(page.getByRole('heading', { name: 'Members' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Transfer ownership' })).toHaveCount(0)
    const viewerRow = page.getByRole('listitem').filter({ hasText: '(vieweruser)' })
    await viewerRow.getByLabel('Role').selectOption('viewer')
    await expect(viewerRow.getByLabel('Role')).toHaveValue('viewer')
  })

  test('editor and viewer have read-only collection access', async ({ page }) => {
    for (const username of ['editoruser', 'vieweruser']) {
      await login(page, username)
      await page.goto(collectionPath)
      await expect(page.getByRole('heading', { name: 'Browser collection' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Edit details' })).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Delete collection' })).toHaveCount(0)
      await expect(page.getByRole('heading', { name: 'Members' })).toHaveCount(0)
      await expect(page.getByRole('heading', { name: 'Transfer ownership' })).toHaveCount(0)
    }
  })

  test('outsider and instance admin without membership cannot access the collection', async ({ page }) => {
    await login(page, 'outsideruser')
    await page.goto('/collections')
    await expect(page.getByText('Browser collection')).toHaveCount(0)
    await page.goto(collectionPath)
    await expect(page.getByRole('heading', { name: 'Collection unavailable' })).toBeVisible()

    await login(page, 'secondinstanceadmin')
    await page.goto('/admin/users')
    await expect(page.getByRole('heading', { name: 'Local users' })).toBeVisible()
    await page.goto('/collections')
    await expect(page.getByText('Browser collection')).toHaveCount(0)
    await page.goto(collectionPath)
    await expect(page.getByRole('heading', { name: 'Collection unavailable' })).toBeVisible()
  })

  test('ownership transfer makes the new owner exclusive and keeps the old owner as admin', async ({ page }) => {
    await login(page, 'owneruser')
    await page.goto(collectionPath)
    const transferForm = page.locator('form').filter({ hasText: 'Review transfer' })
    await transferForm.getByLabel('New owner username').fill('adminuser')
    await transferForm.getByRole('button', { name: 'Review transfer' }).click()
    await expect(page.getByText('You will remain an admin member')).toBeVisible()
    await page.getByRole('button', { name: 'Confirm transfer' }).click()
    await expect(page.getByRole('heading', { name: 'Transfer ownership' })).toHaveCount(0)
    await expect(page.getByText('Owner: adminuser (adminuser)')).toBeVisible()
    await expect(page.getByRole('list', { name: 'Collection members' }).getByText('(owneruser)')).toBeVisible()
    await expect(page.getByRole('list', { name: 'Collection members' }).getByText('(adminuser)')).toHaveCount(0)

    await login(page, 'adminuser')
    await page.goto(collectionPath)
    await expect(page.getByRole('button', { name: 'Delete collection' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Transfer ownership' })).toBeVisible()
  })

  test('instance admin user controls revoke and restore access and protect the final admin', async ({ page, browser }) => {
    await login(page, 'secondinstanceadmin')
    await page.goto('/admin/users')
    await createUser(page, 'managedUser')
    const managedRow = page.getByRole('listitem').filter({ hasText: '(manageduser)' })
    await managedRow.getByRole('button', { name: 'Disable' }).click()
    await page.getByRole('button', { name: 'Confirm disable' }).click()
    await expect(managedRow.getByRole('button', { name: 'Enable' })).toBeVisible()
    await login(page, 'manageduser', password, false)
    await expect(page.getByText('Login failed. Check your credentials and try again.')).toBeVisible()

    await login(page, 'secondinstanceadmin')
    await page.goto('/admin/users')
    await managedRow.getByRole('button', { name: 'Enable' }).click()
    await login(page, 'manageduser')
    await expect(page.getByLabel('Open application menu')).toBeVisible()

    const adminContext = await browser.newContext()
    const adminPage = await adminContext.newPage()
    await login(adminPage, 'secondinstanceadmin')
    await adminPage.goto('/admin/users')
    const resetRow = adminPage.getByRole('listitem').filter({ hasText: '(manageduser)' })
    await resetRow.getByRole('button', { name: 'Reset password' }).click()
    const resetForm = adminPage.locator('form').last()
    await resetForm.getByLabel('New password', { exact: true }).fill('a changed sufficiently long password')
    await resetForm.getByLabel('Confirm new password').fill('a changed sufficiently long password')
    await resetForm.getByRole('button', { name: 'Reset password' }).click()
    await expect(adminPage.getByText('Password reset for manageduser')).toBeVisible()
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Sign in to Stashive' })).toBeVisible()
    await page.getByLabel('Username').fill('manageduser')
    await page.getByLabel('Password').fill(password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Login failed. Check your credentials and try again.')).toBeVisible()
    await login(page, 'manageduser', 'a changed sufficiently long password')
    await expect(page.getByLabel('Open application menu')).toBeVisible()

    const ownerRow = adminPage.getByRole('listitem').filter({ hasText: '(owneruser)' })
    await ownerRow.getByRole('button', { name: 'Disable' }).click()
    const [ownerDisableResponse] = await Promise.all([
      adminPage.waitForResponse((response) =>
        response.url().includes('/api/admin/users/') &&
        response.request().method() === 'PATCH' &&
        response.request().postData() === '{"is_active":false}',
      ),
      adminPage.getByRole('button', { name: 'Confirm disable' }).click(),
    ])
    expect(ownerDisableResponse.status()).toBe(200)
    await expect(ownerRow.getByText('Disabled', { exact: true })).toBeVisible()
    const ownRow = adminPage.getByRole('listitem').filter({ hasText: '(secondinstanceadmin)' })
    const [removeAdminResponse] = await Promise.all([
      adminPage.waitForResponse((response) =>
        response.url().includes('/api/admin/users/') &&
        response.request().method() === 'PATCH' &&
        response.request().postData() === '{"is_instance_admin":false}',
      ),
      ownRow.getByRole('button', { name: 'Remove admin' }).click(),
    ])
    expect(removeAdminResponse.status()).toBe(409)
    await expect(adminPage.getByText('At least one active instance admin must remain.')).toBeVisible()
    await expect(ownRow.getByText('Instance admin', { exact: true })).toBeVisible()
    await expect(ownRow.getByRole('button', { name: 'Remove admin' })).toBeVisible()
    await expect(adminPage.getByRole('heading', { name: 'Local users' })).toBeVisible()
    await adminContext.close()
  })
})
