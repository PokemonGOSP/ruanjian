import { expect, test } from '@playwright/test'

async function login(page, username, password) {
  await page.goto('/login')
  await page.getByLabel('用户名').fill(username)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page.getByRole('heading', { name: '首页 / Dashboard' })).toBeVisible()
}

test('anonymous visitors are redirected to login', async ({ page }) => {
  await page.goto('/activities')

  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: '高校社团活动管理系统' })).toBeVisible()
})

test('invalid credentials stay on login with an error', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('用户名').fill('student01')
  await page.getByLabel('密码').fill('wrong-password')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page.locator('.error')).toHaveText('用户名或密码错误')
  await expect(page).toHaveURL(/\/login$/)
})

test('student can log in, browse every module and log out', async ({ page }) => {
  await login(page, 'student01', 'Student123!')
  await expect(page.locator('header')).toContainText('学生一')

  const pages = [
    ['/clubs', '社团注册与年审'],
    ['/members', '成员管理'],
    ['/activities', '活动管理'],
    ['/finance', '经费记录（M05）'],
    ['/notifications', '通知中心（M06）'],
    ['/reports', '统计与审计（M07）'],
    ['/accounts', '账号与角色授权（M01 / FR-23）'],
  ]
  for (const [path, heading] of pages) {
    await page.goto(path)
    await expect(page).toHaveURL(new RegExp(`${path}$`))
    await expect(page.getByRole('heading', { name: heading })).toBeVisible()
  }

  await expect(page.getByText('当前身份没有 R04 权限')).toBeVisible()

  await page.getByRole('button', { name: '退出' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: '高校社团活动管理系统' })).toBeVisible()
})

test('admin sees account management and audit logs', async ({ page }) => {
  await login(page, 'admin01', 'Admin123!')

  await page.goto('/accounts')
  await expect(page.getByRole('heading', { name: '账号与角色授权（M01 / FR-23）' })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建账号' })).toBeVisible()
  await expect(page.locator('table').getByText('student01')).toBeVisible()

  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: '统计与审计（M07）' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '审计日志（R04）' })).toBeVisible()
})

test('club leader sees finance data and activity creation', async ({ page }) => {
  await login(page, 'leader01', 'Leader123!')

  await page.goto('/finance')
  await expect(page.getByRole('heading', { name: '经费记录（M05）' })).toBeVisible()
  await expect(page.getByText('收入合计')).toBeVisible()

  await page.goto('/activities')
  await expect(page.getByRole('heading', { name: '活动管理' })).toBeVisible()
  await expect(page.getByRole('button', { name: '+ 新建活动' })).toBeVisible()

  await page.goto('/reports')
  await expect(page.getByRole('heading', { name: '统计与审计（M07）' })).toBeVisible()
  await expect(page.getByRole('button', { name: '导出经费 CSV' })).toBeVisible()

  await page.goto('/clubs')
  await expect(page.getByRole('heading', { name: '社团注册与年审' })).toBeVisible()
})
