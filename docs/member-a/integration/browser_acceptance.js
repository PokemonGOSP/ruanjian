// 成员 A 浏览器验收脚本（需要后端 + 前端已启动，且已安装 playwright-core）
// 用法：
//   npm install playwright-core
//   node browser_acceptance.js
// 可选环境变量：APP_BASE、CHROME_PATH、SCREENSHOTS_DIR
// 默认截图目录：成员A/docs/screenshots
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');

const BASE = process.env.APP_BASE || 'http://127.0.0.1:5173';
const SHOTS = process.env.SCREENSHOTS_DIR || path.join(__dirname, '..', 'docs', 'screenshots');
fs.mkdirSync(SHOTS, { recursive: true });

const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
const clubName = `成员A浏览器验收社团${stamp}`;
const credentials = {
  student01: 'Student123!',
  student02: 'Student123!',
  manager01: 'Manager123!',
  leader01: 'Leader123!',
};

async function login(page, username) {
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await page.locator('input[autocomplete="username"]').fill(username);
  await page.locator('input[type="password"]').fill(credentials[username]);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await page.getByRole('heading', { name: '首页 / Dashboard' }).waitFor({ timeout: 15000 });
}

async function logout(page) {
  await page.getByRole('button', { name: '退出', exact: true }).click();
  await page.getByRole('heading', { name: '高校社团活动管理系统' }).waitFor({ timeout: 15000 });
}

async function goClubs(page) {
  await page.getByRole('link', { name: '社团/年审' }).click();
  await page.getByRole('heading', { name: '社团注册与年审' }).waitFor({ timeout: 15000 });
}

async function goMembers(page) {
  await page.getByRole('link', { name: '成员', exact: true }).click();
  await page.getByRole('heading', { name: '成员管理' }).waitFor({ timeout: 15000 });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  // 预期会出现的网络 4xx：favicon 404，以及 R03 打开名册时的 403。
  // 浏览器会把它们打印成 console error，这里只保留未捕获的 JS 错误。
  page.on('response', (response) => {
    const url = response.url();
    const status = response.status();
    if (status >= 500) errors.push(`server ${status}: ${url}`);
  });

  // 1. student02 创建并提交注册申请
  await login(page, 'student02');
  await goClubs(page);
  await page.getByRole('button', { name: '新建注册申请', exact: true }).click();
  await page.getByLabel('拟用社团名称').fill(clubName);
  await page.getByLabel('社团简介').fill('成员A 浏览器验收用虚构社团');
  await page.getByLabel('指导教师联系方式（可选）').fill('browser-test@example.com');
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  await page.getByText('社团注册申请已创建为草稿').waitFor({ timeout: 10000 });
  const draftRow = page.locator('tr').filter({ hasText: clubName });
  await draftRow.getByRole('button', { name: '提交', exact: true }).click();
  await page.getByText('社团注册申请已提交，等待 R03 审核').waitFor({ timeout: 10000 });
  await shot(page, '01-注册申请已提交');
  await logout(page);

  // 2. manager01 审核通过
  await login(page, 'manager01');
  await goClubs(page);
  const pendingRow = page.locator('tr').filter({ hasText: clubName });
  await pendingRow.getByRole('button', { name: '审核', exact: true }).click();
  await page.getByLabel('结果').selectOption('APPROVED');
  await page.getByLabel('审核意见').fill('浏览器验收：材料齐全，通过');
  await page.getByRole('button', { name: '确认审核', exact: true }).click();
  await page.getByText('审核通过，已建立社团并授予申请人 R02').waitFor({ timeout: 10000 });
  await shot(page, '02-注册审核通过');
  await logout(page);

  // 3. student02 刷新身份，确认新社团 R02
  await login(page, 'student02');
  await goClubs(page);
  await page.getByRole('button', { name: '刷新身份与授权', exact: true }).click();
  await page.getByText('身份与社团授权已刷新').waitFor({ timeout: 10000 });
  await page.getByRole('link', { name: '首页', exact: true }).click();
  await page.getByRole('heading', { name: '首页 / Dashboard' }).waitFor({ timeout: 10000 });
  const dashboardText = await page.locator('body').innerText();
  assert.ok(dashboardText.includes(clubName), '首页应出现新社团 R02 授权');
  await shot(page, '03-申请人获得R02授权');
  await logout(page);

  // 4. student02 创建并提交年审，manager01 驳回
  await login(page, 'student02');
  await goClubs(page);
  await page.getByRole('button', { name: '年审', exact: true }).click();
  await page.getByRole('button', { name: '新建年审申请', exact: true }).click();
  await page.getByLabel('社团').selectOption({ label: clubName });
  await page.getByLabel('年度').fill('2099');
  await page.getByLabel('年审材料').fill('浏览器验收虚构年审材料');
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  await page.getByText('年审申请已创建为草稿').waitFor({ timeout: 10000 });
  const annualRow = page.locator('tr').filter({ hasText: clubName }).filter({ hasText: '2099' });
  await annualRow.getByRole('button', { name: '提交', exact: true }).click();
  await page.getByText('年审申请已提交，等待 R03 审核').waitFor({ timeout: 10000 });
  await shot(page, '04-年审已提交');
  await logout(page);

  await login(page, 'manager01');
  await goClubs(page);
  await page.getByRole('button', { name: '年审', exact: true }).click();
  const reviewAnnualRow = page.locator('tr').filter({ hasText: clubName }).filter({ hasText: '2099' });
  await reviewAnnualRow.getByRole('button', { name: '审核', exact: true }).click();
  await page.getByLabel('结果').selectOption('REJECTED');
  await page.getByLabel('审核意见').fill('浏览器验收：材料不完整，驳回');
  await page.getByRole('button', { name: '确认审核', exact: true }).click();
  await page.getByText('年审审核结果已保存').waitFor({ timeout: 10000 });
  await shot(page, '05-年审驳回且社团未冻结');
  await logout(page);

  // 5. student01 申请入团，student02 处理并维护职务
  await login(page, 'student01');
  await goMembers(page);
  await page.getByRole('button', { name: '提交成员申请', exact: true }).click();
  await page.getByLabel('目标社团').selectOption({ label: clubName });
  await page.getByLabel('申请类型').selectOption('JOIN');
  await page.getByLabel('说明（可选）').fill('浏览器验收：希望加入社团');
  await page.getByRole('button', { name: '提交申请', exact: true }).click();
  await page.getByText('成员申请已提交，等待目标社团 R02 处理').waitFor({ timeout: 10000 });
  await shot(page, '06-入团申请已提交');
  await logout(page);

  await login(page, 'student02');
  await goMembers(page);
  await page.getByLabel('范围').selectOption({ label: '我负责社团的申请' });
  const membershipRow = page.locator('tr').filter({ hasText: clubName }).filter({ hasText: '学生一' });
  await membershipRow.getByRole('button', { name: '处理', exact: true }).click();
  await page.getByLabel('结果').selectOption('APPROVED');
  await page.getByLabel('处理意见').fill('浏览器验收：同意入团');
  await page.getByRole('button', { name: '确认处理', exact: true }).click();
  await page.getByText('成员申请已同意，成员关系已同步更新').waitFor({ timeout: 10000 });
  await shot(page, '07-入团申请已同意');

  await page.getByRole('button', { name: '成员名册', exact: true }).click();
  await page.getByLabel('社团').selectOption({ label: clubName });
  await page.getByText('学生一').first().waitFor({ timeout: 10000 });
  const memberRow = page.locator('tr').filter({ hasText: '学生一' });
  await memberRow.getByRole('button', { name: '维护职务', exact: true }).click();
  await page.locator('input.inline-input').fill('浏览器验收职务');
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.getByText('社团职务已更新').waitFor({ timeout: 10000 });
  await shot(page, '08-成员名册与职务');
  await logout(page);

  // 6. R03 不应看到 M03 全量名册：用 manager01 打开名册应被拒绝
  await login(page, 'manager01');
  await goMembers(page);
  await page.getByRole('button', { name: '成员名册', exact: true }).click();
  await page.getByLabel('社团').selectOption({ label: clubName });
  await page.getByText('只有本社团负责人或有效成员可以查看名册').waitFor({ timeout: 10000 });
  await shot(page, '09-R03名册越权被拒绝');
  await logout(page);

  assert.deepEqual(errors, [], `浏览器控制台错误: ${errors.join(' | ')}`);
  await browser.close();
  console.log(JSON.stringify({ clubName, screenshots: fs.readdirSync(SHOTS).sort() }, null, 2));
  console.log('BROWSER ACCEPTANCE PASS');
})().catch((error) => {
  console.error('BROWSER ACCEPTANCE FAIL');
  console.error(error);
  process.exit(1);
});
