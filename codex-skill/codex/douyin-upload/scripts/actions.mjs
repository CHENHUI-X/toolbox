import { access } from 'node:fs/promises';

export const manageUrl = 'https://creator.douyin.com/creator-micro/content/manage';
const uploadUrl = 'https://creator.douyin.com/creator-micro/content/upload';
const titlePlaceholder = '填写作品标题，为作品获得更多流量';
const manageUrlPattern = '**/creator-micro/content/manage**';
const shown = locator => locator.isVisible().catch(() => false);
const escapeRegex = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

async function declaration(page, value) {
  const trigger = page.getByText('请选择自主声明', { exact: true });
  await trigger.click();
  await page.locator('label.semi-radio').filter({ hasText: value || '无需添加自主声明' }).click();
  await page.getByRole('button', { name: '确定', exact: true }).click();
}

async function topics(page, item) {
  const editor = page.locator('[contenteditable=true]').first();
  await editor.press('Escape');
  await editor.focus();
  await editor.press('ControlOrMeta+A');
  await editor.press('Backspace');
  await page.waitForFunction(() => document.querySelector('[contenteditable=true]')?.innerText.replace(/\u200b/g, '').trim() === '', null, { timeout: 5000 });
  await page.keyboard.insertText(item.caption.trim() + '\n\n');
  item.selectedTopics = [];
  for (const topic of [...new Set(item.topics || [])]) {
    if (item.selectedTopics.length === 5) break;
    await editor.press('ControlOrMeta+End');
    await editor.pressSequentially(`#${topic}`, { delay: 20 });
    const option = page.locator('.mention-suggest-mount-dom').getByText(topic, { exact: true });
    try {
      await option.waitFor({ state: 'visible', timeout: 6000 });
    } catch {
      await editor.press('Escape');
      for (const _ of `#${topic}`) await editor.press('Backspace');
      continue;
    }
    await option.click();
    await editor.locator('[data-mention="#"]').filter({ hasText: new RegExp('^\\s*#' + escapeRegex(topic) + '\\s*$') }).waitFor({ timeout: 5000 });
    item.selectedTopics.push(topic);
    await editor.press('ControlOrMeta+End');
    await page.keyboard.insertText(' ');
  }
  if (item.selectedTopics.length !== 5) throw new Error(`平台话题未选满 5 个，实际 ${item.selectedTopics.length} 个`);
  if (await editor.locator('[data-mention="#"]').count() !== 5) throw new Error('实际话题标签数量不匹配');
}

async function cover(page, file, index) {
  if (!file) throw new Error(`缺少第 ${index === 0 ? '竖' : '横'} 张封面文件`);
  await access(file);
  const control = page.locator('[class^="coverControl-"]').nth(index);
  const oldSource = await control.locator('img').getAttribute('src').catch(() => null);
  await control.waitFor({ state: 'visible' });
  await control.click();
  await page.waitForFunction(() => [...document.querySelectorAll('[role=dialog] button')].some(b => b.textContent.trim() === '完成' && !b.disabled), null, { timeout: 25000 });
  const oldCanvas = await page.locator('[role=dialog] canvas.lower-canvas:visible').first().evaluate(c => c.toDataURL());
  const input = page.locator('.semi-upload:has-text("点击上传文件或拖拽文件到这里") input.semi-upload-hidden-input');
  await input.waitFor({ state: 'attached' });
  await input.setInputFiles(file);
  await page.waitForFunction(old => {
    const canvas = [...document.querySelectorAll('[role=dialog] canvas.lower-canvas')].find(c => c.getBoundingClientRect().width > 300);
    return canvas && canvas.toDataURL() !== old;
  }, oldCanvas, { timeout: 30000 });
  const done = page.getByRole('button', { name: '完成', exact: true });
  await done.waitFor({ state: 'visible', timeout: 30000 });
  await done.click({ timeout: 90000 });
  const skip = page.getByRole('button', { name: '暂不设置', exact: true });
  if (await shown(skip)) await skip.click();
  await page.locator('[role=dialog]').last().waitFor({ state: 'hidden', timeout: 30000 });
  await page.waitForFunction(({ index, oldSource }) => {
    const source = document.querySelectorAll('[class^="coverControl-"]')[index]?.querySelector('img')?.src;
    return source && source !== oldSource;
  }, { index, oldSource }, { timeout: 30000 });
}

export async function prepare(page, item) {
  await page.goto(uploadUrl, { waitUntil: 'domcontentloaded' });
  await page.locator('input[type=file][accept*="video"]').setInputFiles(item.video);
  const title = page.getByPlaceholder(titlePlaceholder, { exact: true });
  await title.waitFor({ timeout: 180000 });
  await title.fill(item.title);
  const tip = page.getByText('我知道了', { exact: true });
  if (await shown(tip)) await tip.click();
  await topics(page, item);
  await declaration(page, item.declaration);
  await page.locator('label').filter({ hasText: /^\s*公开\s*$/ }).click();
  await page.locator('label').filter({ hasText: /^\s*立即发布\s*$/ }).click();
  await cover(page, item.cover, 0);
  await cover(page, item.coverHorizontal, 1);
  await title.fill(item.title);
  await page.waitForFunction(() => /上传失败|预览封面\/标题/.test(document.body.innerText), null, { timeout: 180000 });
  if ((await page.locator('body').innerText()).includes('上传失败')) throw new Error('视频上传失败');
  return page;
}

export async function publish(page, item, log) {
  const publishButton = page.getByRole('button', { name: '发布', exact: true });
  await publishButton.waitFor({ state: 'visible' });
  await publishButton.click();
  const verification = page.getByText('使用原设备扫码', { exact: true });
  const result = await Promise.race([
    page.waitForURL(manageUrlPattern, { waitUntil: 'domcontentloaded', timeout: 60000 }).then(() => 'submitted'),
    verification.waitFor({ state: 'visible', timeout: 60000 }).then(() => 'verification'),
  ]);
  if (result === 'verification') {
    await verification.click();
    await page.bringToFront();
    if (typeof log === 'function') log({ event: 'verification_required', episode: item.episode, title: item.title });
    await page.waitForURL(manageUrlPattern, { waitUntil: 'domcontentloaded', timeout: 600000 });
  }
  return { submitted: true, url: page.url() };
}

export async function openCollection(page, name, editUrl) {
  if (editUrl) {
    const url = new URL(editUrl);
    if (url.origin !== 'https://creator.douyin.com' || !url.pathname.startsWith('/creator-micro/content/collection/detail/')) throw new Error('collectionUrl 不是抖音合集编辑地址');
    await page.goto(editUrl, { waitUntil: 'domcontentloaded' });
  } else {
    await page.goto(manageUrl + '?tab=collections', { waitUntil: 'domcontentloaded' });
    await page.getByText(name, { exact: true }).locator('xpath=../../..').getByRole('button', { name: '编辑合集', exact: true }).click();
  }
  await page.waitForFunction(name => document.querySelector('input[placeholder="请输入合集的标题"]')?.value === name, name, { timeout: 30000 });
  return page.url();
}

function statusOf(text) {
  if (text.includes('已发布')) return 'published';
  if (text.includes('审核中')) return 'reviewing';
  if (text.includes('发布中')) return 'unconfirmed';
  return 'missing';
}

export async function verifyCollection(page, items) {
  const texts = await page.locator('.video-card-t38W_z').allTextContents();
  return items.map(item => {
    const index = texts.findIndex(text => text.includes(item.title));
    const text = index < 0 ? '' : texts[index];
    const order = index < 0 ? null : index + 1;
    return { video: item.video, title: item.title, episode: item.episode, order, orderCorrect: order === item.episode, status: statusOf(text), topicCount: (text.match(/#/g) || []).length };
  });
}

async function addMissing(page, items) {
  const existing = await page.locator('.video-card-t38W_z .info-title-VP_P1k').allTextContents();
  const missing = items.filter(item => !existing.some(text => text.includes(item.title)));
  if (!missing.length) return;
  if (existing.length) await page.getByRole('button', { name: '添加作品', exact: true }).click();
  else await page.getByText('点击添加作品', { exact: true }).click();
  const search = page.getByPlaceholder('请输入作品描述查找作品', { exact: true });
  for (const item of missing) {
    await search.fill(item.title);
    const row = page.locator('.drawer-item-mTdppj').filter({ has: page.locator('.info-title-VP_P1k').filter({ hasText: new RegExp('^' + escapeRegex(item.title) + '(?:\\s|$)') }) });
    const previous = await page.locator('.video-card-t38W_z').count();
    await row.locator('.plus-area-mPEOds').click({ timeout: 15000 });
    await page.waitForFunction(n => document.querySelectorAll('.video-card-t38W_z').length > n, previous);
  }
  await page.getByText('作品列表', { exact: true }).locator('..').locator('span').last().click();
}

export async function finalizeCollection(page, items, editUrl) {
  const savedUrl = await openCollection(page, items[0]?.collection, editUrl);
  await addMissing(page, items);
  const input = page.getByPlaceholder('填写集数', { exact: true });
  for (const item of items) {
    const titles = await page.locator('.video-card-t38W_z .info-title-VP_P1k').allTextContents();
    if (item.episode > titles.length) throw new Error('集数超出合集作品数：' + item.episode);
    if (titles[item.episode - 1]?.startsWith(item.title)) continue;
    const card = page.locator('.video-card-t38W_z').filter({ has: page.locator('.info-title-VP_P1k').filter({ hasText: new RegExp('^' + escapeRegex(item.title) + '(?:\\s|$)') }) });
    await card.waitFor({ state: 'visible' });
    await card.locator('.video-card-index-Hj1U9V').hover();
    await card.locator('.icon-A4c2NN').first().click();
    await input.fill(String(item.episode));
    await page.getByRole('button', { name: '确认修改', exact: true }).click();
    await page.waitForFunction(({ title, index }) => document.querySelectorAll('.video-card-t38W_z .info-title-VP_P1k')[index]?.innerText.startsWith(title), { title: item.title, index: item.episode - 1 });
  }
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await page.waitForURL(manageUrlPattern, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await openCollection(page, items[0].collection, savedUrl);
  const result = await verifyCollection(page, items);
  if (result.some(i => !i.orderCorrect || i.topicCount !== 5 || !['published', 'reviewing'].includes(i.status))) throw new Error('合集保存后核对失败：' + JSON.stringify(result));
  return result;
}

export async function verifyWorks(page, items) {
  await page.goto(manageUrl, { waitUntil: 'domcontentloaded' });
  await page.locator('[class^="video-card-content-"]').first().waitFor();
  const results = [];
  for (const item of items) {
    const locator = page.getByText(new RegExp('^' + escapeRegex(item.title) + '(?:\\s|$)'));
    for (let attempt = 0; !await locator.count() && attempt < 30; attempt++) {
      const previous = await page.locator('[class^="video-card-content-"]').count();
      await page.evaluate(() => [...document.querySelectorAll('*')].filter(e => e.clientHeight > 100 && e.scrollHeight > e.clientHeight + 50 && /auto|scroll/.test(getComputedStyle(e).overflowY)).forEach(e => e.scrollTop = e.scrollHeight));
      try { await page.waitForFunction(n => document.querySelectorAll('[class^="video-card-content-"]').length > n, previous, { timeout: 1500 }); } catch { break; }
    }
    if (await locator.count() > 1) throw new Error('后台存在同名作品，需进一步确认：' + item.title);
    const text = await locator.locator('xpath=../../../..').innerText().catch(() => '');
    results.push({ video: item.video, title: item.title, status: statusOf(text) });
  }
  return results;
}
