import { readFile, writeFile, rename, mkdir, stat } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';
import { prepare, publish, finalizeCollection, verifyWorks, manageUrl } from './actions.mjs';

const completed = new Set(['submitted', 'reviewing', 'published']);
const uncertain = new Set(['publishing', 'publish_unconfirmed']);
export const log = event => console.log(JSON.stringify({ time: new Date().toISOString(), ...event }));

export async function loadManifest(filename) {
  const raw = JSON.parse(await readFile(filename, 'utf8'));
  const rows = Array.isArray(raw) ? raw : raw.items;
  if (!Array.isArray(rows) || !rows.length) throw new Error('清单 items 不能为空');
  const base = path.dirname(path.resolve(filename));
  const ids = new Set(), orders = new Set();
  const items = rows.map(row => {
    const collection = row.collection ?? raw.collection ?? '';
    const title = String(row.title || '').trim().replace(collection ? /^第\s*[\d一二三四五六七八九十百零两]+\s*集\s*[:：、.\-—|]?\s*/u : /$^/, '');
    if (!title || [...title].length > 30) throw new Error('标题为空或超过 30 字：' + title);
    const episode = Number(row.episode);
    if (!Number.isInteger(episode) || episode < 1) throw new Error('episode 必须是正整数');
    const topics = [...new Set((row.topics || []).map(t => String(t).replace(/^#/, '').trim()).filter(Boolean))];
    if (topics.length < 5 || topics.length > 10) throw new Error('请提供 5–10 个相关话题候选：' + title);
    const files = {};
    for (const field of ['video', 'cover', 'coverHorizontal']) {
      if (!row[field]) throw new Error('缺少字段 ' + field + '：' + title);
      files[field] = path.resolve(base, row[field]);
    }
    const key = collection + ':' + episode;
    if (ids.has(files.video) || orders.has(key)) throw new Error('重复视频或重复集数：' + title);
    ids.add(files.video); orders.add(key);
    const caption = String(row.caption || '').replace(/(?:^|\s)#[^\s#]+(?:\s+#[^\s#]+)*\s*$/u, '').trim();
    if (!caption) throw new Error('缺少发布正文：' + title);
    return { episode, title, caption, topics, collection, collectionUrl: row.collectionUrl ?? raw.collectionUrl, declaration: row.declaration || '无需添加自主声明', ...files };
  }).sort((a, b) => a.episode - b.episode);
  await Promise.all(items.flatMap(item => ['video', 'cover', 'coverHorizontal'].map(async field => {
    const s = await stat(item[field]).catch(() => { throw new Error('文件不存在：' + item[field]); });
    if (!s.isFile() || !s.size) throw new Error('文件为空或不是普通文件：' + item[field]);
  })));
  return items;
}

export async function loadState(filename) {
  try { return JSON.parse(await readFile(filename, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return {}; throw error; }
}

export function plan(items, state) {
  return items.map(item => ({ episode: item.episode, title: item.title, action: uncertain.has(state[item.video]?.status) ? 'reconcile' : completed.has(state[item.video]?.status) ? 'skip' : 'upload' }));
}

export async function runWithContext(context, options) {
  const items = await loadManifest(options.manifest);
  const stateFile = path.resolve(options.state || path.join(path.dirname(options.manifest), '.douyin-upload-state.json'));
  const state = await loadState(stateFile);
  const schedule = plan(items, state);
  if (options.plan) return { plan: schedule };
  if (!options.verify && schedule.some(i => i.action === 'reconcile')) throw new Error('有发布结果未知的条目；先用 --verify 核对后台，禁止再次发布');
  const concurrency = Number(options.concurrency || 4);
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 4) throw new Error('concurrency 范围为 1–4');
  let writes = Promise.resolve();
  const update = async (item, status, extra = {}) => {
    state[item.video] = { ...state[item.video], episode: item.episode, title: item.title, status, updatedAt: new Date().toISOString(), ...extra };
    const snapshot = JSON.stringify(state, null, 2);
    writes = writes.then(async () => {
      await mkdir(path.dirname(stateFile), { recursive: true });
      await writeFile(stateFile + '.tmp', snapshot, { mode: 0o600 });
      await rename(stateFile + '.tmp', stateFile);
    });
    await writes;
    log({ event: status, episode: item.episode, title: item.title, ...extra });
  };
  const pending = items.filter(item => !completed.has(state[item.video]?.status));
  const pages = [];
  if (!options.verify) {
    for (let i = 0; i < Math.min(concurrency, pending.length); i++) pages.push(await context.newPage());
    for (let offset = 0; offset < pending.length; offset += concurrency) {
      const group = pending.slice(offset, offset + concurrency);
      const jobs = group.map(async (item, index) => {
        const page = pages[index];
        page.setDefaultTimeout(10000);
        for (let attempt = 0; attempt < 2; attempt++) {
          await update(item, 'preparing', { attempt: attempt + 1 });
          try {
            await prepare(page, item);
            await update(item, 'prepared', { selectedTopics: item.selectedTopics });
            return;
          } catch (error) {
            if (!attempt) { log({ event: 'prepare_retry', episode: item.episode, error: error.message }); continue; }
            await update(item, 'prepare_failed', { error: error.message });
            throw error;
          }
        }
      });
      const ready = await Promise.allSettled(jobs);
      if (ready.some(r => r.status === 'rejected')) throw new Error('准备失败，尚未继续发布；查看 prepare_failed 的具体错误');
      for (let index = 0; index < group.length; index++) {
        const item = group[index];
        await update(item, 'publishing');
        try {
          await publish(pages[index], item, log);
          await update(item, 'submitted');
        } catch (error) {
          await update(item, 'publish_unconfirmed', { error: error.message });
          throw error;
        }
      }
    }
  }
  const admin = await context.newPage();
  admin.setDefaultTimeout(10000);
  const groups = Map.groupBy(items, item => item.collection);
  const results = [];
  for (const [name, group] of groups) {
    const url = options.collectionUrl || group[0].collectionUrl;
    let verified;
    if (!name) verified = await verifyWorks(admin, group);
    else if (options.verify) verified = await verifyWorks(admin, group);
    else verified = await finalizeCollection(admin, group, url);
    for (const result of verified) {
      const item = group.find(i => i.video === result.video);
      if (['published', 'reviewing'].includes(result.status)) await update(item, result.status, { verification: result });
    }
    results.push(...verified);
  }
  for (const page of pages) await page.close();
  await admin.bringToFront();
  const summary = { event: 'finished', published: results.filter(i => i.status === 'published').length, reviewing: results.filter(i => i.status === 'reviewing').length, unresolved: results.filter(i => !['published', 'reviewing'].includes(i.status)).length, stateFile, results };
  log(summary);
  return summary;
}

async function main() {
  const options = {};
  for (let i = 2; i < process.argv.length; i++) {
    const key = process.argv[i].replace(/^--/, '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    if (['plan', 'verify', 'help'].includes(key)) options[key] = true;
    else options[key] = process.argv[++i];
  }
  if (options.help || !options.manifest) {
    console.log('node upload.mjs --manifest upload.json [--plan | --verify] [--profile PATH] [--state PATH] [--concurrency 4] [--collection-url URL] [--playwright PATH]');
    return;
  }
  options.manifest = path.resolve(options.manifest);
  if (options.plan) { console.log(JSON.stringify(await runWithContext(null, options), null, 2)); return; }
  const packagePath = options.playwright || process.env.DOUYIN_PLAYWRIGHT_PATH;
  const { chromium } = packagePath ? await import(pathToFileURL(path.resolve(packagePath)).href) : await import('playwright');
  const profile = path.resolve(options.profile || path.join(os.homedir(), '.codex/runtime/douyin-upload/profile'));
  await mkdir(profile, { recursive: true, mode: 0o700 });
  const context = await chromium.launchPersistentContext(profile, { channel: 'chrome', headless: false, viewport: { width: 1440, height: 1000 } });
  context.setDefaultTimeout(10000);
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(manageUrl, { waitUntil: 'domcontentloaded' });
    const loggedIn = await page.waitForFunction(() => document.body.innerText.includes('作品合集'), null, { timeout: 10000 }).then(() => true, () => false);
    if (!loggedIn) log({ event: 'login_required', message: '请在可见 Chrome 完成抖音登录' });
    await page.waitForFunction(() => document.body.innerText.includes('作品合集'), null, { timeout: 600000 });
    const result = await runWithContext(context, options);
    if (result.unresolved) process.exitCode = 1;
  } finally { await context.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main().catch(error => { console.error(JSON.stringify({ event: 'failed', error: error.message })); process.exitCode = 1; });
