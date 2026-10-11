# 输入与运行

默认 Node 22+、Chrome、Playwright。首次登录需要用户完成，后续保留同一个 profile；不复制 Cookie、不打印凭据、不关闭无关 Chrome。

## 清单

```json
{
  "collection": "一分钟搞懂一件事",
  "items": [
    {
      "episode": 21,
      "title": "具体的问题标题",
      "caption": "已有的发布正文，不在这里拼纯文字话题。",
      "topics": ["一分钟搞懂一件事", "生活科普", "具体主题", "知识领域", "使用场景"],
      "video": "选题目录/成片.mp4",
      "cover": "选题目录/封面_AI生成.png",
      "coverHorizontal": "选题目录/封面_AI生成_4比3.png"
    }
  ]
}
```

路径相对于清单目录，也可用绝对路径。兼容直接传入 items 数组。每条可覆盖 `collection`、`collectionUrl`、`declaration`。`episode` 是最终合集中的位置，追加新视频应从已有集数之后继续，不能每批重置为 1。封面文件名可以不同，只需指向上游提供的正确文件。

清单按已有选题/文案一次整理好；5–10 个相关话题候选，脚本最多选中 5 个。标题缺少信息时由 agent 根据现成内容补充，不能编造视频里没有的情节。`--state` 建议固定到项目目录，后续批次共用同一个状态文件，避免重复上传同一视频。

## 本机可复用资源

2026-10-09 已跑通的本地资源，使用前只确认路径是否仍存在：

- 视频项目：`/Users/didi/project/python_projects/my_projcets/自媒体/一分钟弄懂一件事/`。
- 此项目固定状态文件：`/Users/didi/project/python_projects/my_projcets/自媒体/一分钟弄懂一件事/.douyin-upload-state.json`。已存入本次核实的 20 条已发布记录；后续批次使用 `--state` 指向它，继续从第 21 集排起。
- Node：`/Users/didi/.hermes/node/bin/node`，系统 `node` 也可用。
- 已安装 Playwright 入口：`/Users/didi/.codex/.chatgpt-projects/g-p-6ac75d79e4348191aee2a481a13700f3/output/douyin-batch/node_modules/playwright/index.mjs`。使用 `--playwright` 可直接复用，无须重新下载。
- 已登录 profile：`/Users/didi/.codex/.chatgpt-projects/g-p-6ac75d79e4348191aee2a481a13700f3/output/douyin-batch/profile`。使用 `--profile`；如果原进程仍占用它，复用 context，不启动第二个 Chrome。

如果依赖不存在，可在 skill 目录执行 `npm install --ignore-scripts`，使用已安装的 Chrome，不必下载 Chromium。不要把上述 profile、cookies、原上传状态、截图或账号资料打包进 skill。

## 复用已有 context

将调用写入文件或只传短的导入语句：

```javascript
const { runWithContext } = await import('/absolute/path/douyin-upload/scripts/upload.mjs');
await runWithContext(context, {
  manifest: '/absolute/path/upload.json',
  state: '/absolute/path/project/.douyin-upload-state.json',
  concurrency: 4
});
```

不启用 JSON-over-PTY 的逐步点击协议，不启动 HTTP worker 服务，不重新创建多个 profile。一个 Node 进程里的并发准备已经能并行传输文件和填写不同页面。

## 续跑与结果

相同 `--state` 续跑自动跳过已提交、审核中和已发布记录。点击发布后曾中断，先 `--verify` 只读核对；找不到时保留未知状态，由 agent 检查后台，而不是重发。合集若因未过审暂时不能添加，保留已提交状态，审核通过后重跑，仅补齐合集。

`--plan` 只读检查清单/文件和状态，不启动浏览器、不上传、不写状态；`--verify` 只读访问平台并更新本地核对结果，不点发布、不修改合集。正常上传只有最终一次后台核对，不逐条重开编辑器检查。

仅记录必要状态与错误。若 UI 变更，优先检查 `scripts/actions.mjs` 中的失败选择器；页面元素优先文字/角色，确需类名时用已观察到的前缀，不反复全站探索。
