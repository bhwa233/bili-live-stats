# Danmakus API 完整参考

> 实测时间：2026-10-18
> 站点：[danmakus.com](https://danmakus.com)（B 站弹幕/直播数据监控站，laplace.live 的后端数据源）
> **官方 Swagger**：<https://ukamnads.icu/swagger>（spec: `/swagger/v2/swagger.json`，共 86 个端点）

---

## 基础信息

| 项 | 值 |
|---|---|
| API 入口 | `https://danmakus.com/api/v2`（同域，302 跳转到下者） |
| 实际域名 | `https://ukamnads.icu/api/v2` |
| 协议 | HTTPS / REST / JSON（部分 v3 接口返回 msgpack 二进制） |
| 鉴权 | **无**（不需要 key / cookie / token） |
| CORS | `Access-Control-Allow-Origin: *` |
| 服务端 | Caddy + Kestrel (.NET) |
| 使用条款 | **无**（`/terms`、`/privacy`、`/robots.txt` 均不存在） |

### 调用方式

普通 HTTP 客户端即可，无特殊 header、无需模拟浏览器：

```python
import requests
r = requests.get("https://danmakus.com/api/v2/site", timeout=30)
# requests 默认跟随 302，r.json() 直接可用
```

```bash
curl -L "https://danmakus.com/api/v2/site"    # 不加 -L 只会拿到 302
```

> 若本机请求失败并返回 `000`，先检查 `HTTP_PROXY` / `HTTPS_PROXY` 是否指向了不可用的代理，与服务端无关。

### 通用响应包装

```json
{ "code": 200, "message": "成功", "data": { ... } }
```

失败时 `code` 非 200，`message` 为原因（如 `{"code":404,"message":"未找到","data":null}`）。

---

## 端点总览（86 个）

### Account（15）— 需登录，本项目不使用

```
GET  /api/v2/account/info                     账号信息
GET  /api/v2/account/statistics               贡献统计
POST /api/v2/account/statistics/report
GET  /api/v2/account/channel-lives            已观测的直播场
GET  /api/v2/account/contributed-lives        已贡献的直播场
GET  /api/v2/account/recording                录制记录
GET  /api/v2/account/add-record
GET  /api/v2/account/del-record
GET  /api/v2/account/search-points            查询积分
GET  /api/v2/account/search-points/history    积分历史
GET  /api/v2/account/core-config              客户端配置
POST /api/v2/account/core-config
POST /api/v2/account/update-name
POST /api/v2/account/update-public-profile
POST /api/v2/account/update-recording-setting
```

### DanmakuControllers（31）— 主数据接口

```
GET  /api/v2/site                     站点宏观统计 ★
GET  /api/v2/channels                 全站频道列表（27MB）★
GET  /api/v2/channel                  单主播 + 全部场次 ★
GET  /api/v2/simpleChannel            主播精简信息
GET  /api/v2/channel/filter           频道筛选（GET / POST）
GET  /api/v2/live                     单场直播明细 ★
GET  /api/v2/living                   当前在播（?includeExtra=true）
GET  /api/v2/rank/month               月度榜（支持 area）★★★
GET  /api/v2/rank/day                 日榜（支持 area）
GET  /api/v2/rank/range               时间范围榜（参数格式未明，易 400）
GET  /api/v2/vup-list                 虚拟主播专项列表 ★
GET  /api/v2/area                     分区树（一级 → 二级）
GET  /api/v2/guilds                   公会/MCN 查询
GET  /api/v2/popularChannels          热门频道
GET  /api/v2/popularUsers             热门用户
GET  /api/v2/user                     UP 主信息
GET  /api/v2/user/name                用户名查询
GET  /api/v2/user/watchedChannels
GET  /api/v2/user/watchedChannelsSimple
GET  /api/v2/emoicons                 表情列表
GET  /api/v2/add                      收录投稿（提交直播间）
GET  /api/v2/comment/get              站内评论
POST /api/v2/comment/add
GET  /api/v2/live/comment/get         场次评论
POST /api/v2/live/comment/add
GET  /api/v2/user/comment/get
POST /api/v2/user/comment/add
GET  /api/v2/chat/get                 站内聊天
POST /api/v2/chat/add
GET  /api/v2/chat/tag
```

### AudienceLeaderboard（2）— 观众榜

```
GET  /api/v2/channel/audience-leaderboard    单主播的观众排行
GET  /api/v2/rank/audience/day               全站观众日榜
```

### DanmakuSearch（4）— 弹幕全文搜索

```
GET  /api/v2/danmaku/search                  同步搜索
POST /api/v2/danmaku/search/async            异步任务
GET  /api/v2/danmaku/search/async/{taskId}   任务结果
GET  /api/v2/danmaku/search/queue-stats      队列状态
```

### Contribution（8）— 贡献者（录制客户端用户）

```
GET  /api/v2/contribution/overview
GET  /api/v2/contribution/hub
GET  /api/v2/contribution/areas
GET  /api/v2/contribution/contributor
GET  /api/v2/contribution/me
GET  /api/v2/contribution/minute-today
GET  /api/v2/contribution/rank/day
GET  /api/v2/contribution/rank/range
```

### DanmakuV3（8）— v3 版本，性能更好

```
GET  /api/v3/lives/{liveId}                  单场信息
GET  /api/v3/lives/{liveId}/full             全量（含统计）
GET  /api/v3/lives/{liveId}/delta            增量变更
GET  /api/v3/lives/{liveId}/danmakus         弹幕列表
GET  /api/v3/meta/index-background           首页轮播（msgpack）
GET  /api/v3/meta/emoicons
GET  /api/v3/users/{userId}/bootstrap        用户初始化数据包 ★
GET  /api/v3/users/{userId}/history          用户历史 ★
```

### 其他

```
GET    /api/v3/lives/{liveId}/danmakus/after           弹幕游标翻页
GET    /api/v3/lives/{liveId}/danmakus-with-identities 带匿名身份
POST   /api/v2/streamer-status                         主播状态上报
GET    /api/v2/core-runtime/*                          客户端运行时（14 个，含 ws 与上传）
POST   /api/v3/user-analysis-jobs                      用户分析任务（5 个）
```

**带 ★ 的是本项目实际使用或推荐的接口。**

---

## 核心接口详解

### 1. `GET /api/v2/site` — 站点宏观统计

无参数。返回全站总量，是获取「大盘指标」的首选。

```json
{
  "date": 1792303528304,
  "isMaintenance": false,
  "siteName": "弹幕站",
  "siteAPIDocAddress": "https://ukamnads.icu/swagger",
  "totalChannelsCount": 30119,      // 收录频道数
  "totalLivingCount": 2168,         // 当前直播中
  "totalSegmentsCount": 5696073,    // 弹幕片段数
  "totalDanmakusCount": 8817006306, // 累计弹幕 88 亿
  "officialDanmakuSpeed": 0,
  "userDanmakuSpeed": 2000,         // 客户端抓取速率（条/秒）
  "totalDanmakuSpeed": 2000,
  "onlineCount": 48,                // 站点在线人数
  "onlineClientCount": 82,          // 在线录制客户端数
  "recordingCapacity": 1894,        // 录制容量上限
  "recordingCount": 1808,           // 当前占用
  "queryCount": 109584
}
```

> 注意：`totalChannelsCount`（30,119）与 `/channels` 返回的条数（47,056）不一致，后者含已删除/失效条目。

### 2. `GET /api/v2/channels` — 全站频道列表

无参数，返回 47,056 条、约 27MB、耗时约 28 秒。每条是 `channel` 对象（见字段表）。

适合做全站快照、搜索，以及基于累计值的排序（作为 `/rank/*` 的降级方案）。

### 3. `GET /api/v2/channel?uId={mid}` — 主播 + 全部场次

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `uId` | int | 是 | B 站 mid |

返回 `{ channel: {...}, lives: [ ... ] }`。

**`lives` 返回该主播的全部历史场次**，实测 983 场 / 1374 场均完整返回。约 1.2KB/场。

**不支持任何分页**：`limit`、`pageNum`、`pageSize`、`recent` 传进去全部无效，永远返回全量。

### 4. `GET /api/v2/live?liveId={uuid}` — 单场逐条记录

| 参数 | 类型 | 说明 |
|---|---|---|
| `liveId` | str | 必填，取自 `lives[].liveId` |
| `type` | int | 按记录类型过滤（**`type=2` 有 bug，见已知问题**） |
| `pageNum` | int | 页码，从 1 开始 |
| `pageSize` | int | 每页条数，**上限约 200** |

返回 `{ total, pageNum, pageSize, hasMore, data: { channel, live, danmakus[] } }`。

大主播单场可达 8 万条、7.2MB。

### 5. `GET /api/v2/rank/month` — 月度榜 ★★★

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `year` | int | 是 | 年 |
| `month` | int | 是 | 月 |
| `type` | int | 是 | 榜单类型，见下表 |
| `area` | string | 否 | 一级分区名，如 `虚拟主播` |
| `count` | int | 否 | 返回条数；实测可到 30000（返回全部有数据者） |

`type` 取值（实测推断）：

| type | 排序维度 |
|---|---|
| 1 | 观看 |
| 2 | 流水（income） |
| 3 | 弹幕 |
| 4 | 直播场次 |

返回 `data: RankInfo[]`：

```json
{
  "channel": { ...APIChannelInfo },
  "liveIds": ["uuid", ...],
  "watchCount": 2535870,
  "interactionCount": 0,
  "likeCount": 0,
  "paidCount": 0,
  "liveCount": 17,
  "danmakusCount": 2180247,
  "income": 274395.3
}
```

**这是计算「全站/分区月度总流水」的正确方式**：一次请求 `count=30000` 拿回全部有流水的频道，对 `income` 求和即可，无需抽样。

实测（2026-10，01~18 日）：
- 全站：17,638 条，合计 **8,160.6 万元**（101 秒 / 22MB）
- `area=虚拟主播`：5,709 条，合计 **2,396.9 万元**（26 秒 / 7MB）→ 占 **29.4%**

### 6. `GET /api/v2/rank/day` — 日榜

参数同上（`year`+`month`+`day`+`type`），另有 `area`、`count`。

### 7. `GET /api/v2/vup-list` — 虚拟主播专项名单

返回 `{ [mid]: VTBInfo }`，是站内维护的 VUP 名单，可直接用于「只看虚拟主播」的过滤。

### 8. `GET /api/v2/living` — 当前在播

参数 `includeExtra`（bool），返回 `APIChannelInfo[]`。

### 9. `GET /api/v2/area` — 分区树

返回 `{ "一级分区": ["二级分区", ...] }`，用于构造 `area` 过滤参数。

### 10. `GET /api/v3/users/{userId}/bootstrap` 与 `/history`

v3 接口，数据更聚合。`bootstrap` 一次返回用户的基础信息 + 统计，`history` 返回历史。适合替代 `/channel` 的轻量查询（响应更小）。

> v3 接口部分返回 **msgpack 二进制**（如 `meta/index-background`），需 msgpack 解码，不能直接 `json.loads`。

---

## 字段表

### `channel` 对象

| 字段 | 类型 | 含义 |
|---|---|---|
| `uId` | int | B 站 mid |
| `uName` | str | 主播名 |
| `roomId` | int | 直播间号 |
| `faceUrl` | str | 头像 |
| `isLiving` | bool | 是否在播 |
| `isDeleted` | bool | 是否已失效 |
| `title` | str | 最近一场标题 |
| `tags` | array | 标签 |
| `fansCount` | int | 粉丝数 |
| `followCount` | int | 关注数 |
| `totalLiveCount` | int | 累计场次 |
| `totalLiveSecond` | int | 累计时长（秒） |
| `totalDanmakuCount` | int | 累计弹幕 |
| `totalIncome` | float | 累计流水（元） |
| `lastLiveDate` | int | 最近开播时间（ms） |
| `lastLiveIncome` | float | 最近一场流水 |
| `lastLiveDanmakuCount` | int | 最近一场弹幕数 |
| `lastUpdateStatAt` | int | 统计更新时间（ms） |
| `addDate` | str | 收录时间 |

### `lives[]` 场次对象

| 字段 | 类型 | 含义 |
|---|---|---|
| `liveId` | str | 场次 UUID |
| `title` | str | 标题 |
| `startDate` / `stopDate` | int | 起止时间（ms） |
| `totalIncome` | float | **本场流水（元）** |
| `watchCount` | int | 观看人数 |
| `danmakusCount` | int | 弹幕数 |
| `interactionCount` | int | 互动数 |
| `payCount` | int | 付费人数 |
| `likeCount` | int | 点赞数 |
| `maxOnlineCount` | int | 峰值在线 |
| `parentArea` | str | 一级分区 |
| `area` | str | 二级分区 |
| `coverUrl` | str | 封面 |
| `isFinish` / `isFull` / `isMerged` | bool | 结束/完整/已合并 |
| `versions` | array | 断流分段记录 |

### `danmakus[]` 单条记录

| 字段 | 类型 | 含义 |
|---|---|---|
| `uId` / `uName` | int/str | 发送者 |
| `type` | int | 记录类型 |
| `sendDate` | int | 时间（ms） |
| `message` | str | 内容 |
| `price` | float | **金额（元，已是总价）** |
| `count` | int | 数量 |

`type` 编码：

| type | 含义 | 有 price |
|---|---|---|
| 0 | 普通弹幕 | 否 |
| 1 | 礼物 | 是 |
| 2 | 大航海 / 舰长 | 是 |
| 3 | 醒目留言 SC | 是 |
| 4 | 入场 / 看过 | 否 |

---

## 数据口径（必须遵守）

**流水** = `type` ∈ {1, 2, 3} 的 `price` 之和。

- `price` 已是该条记录的总金额，**不要再乘 `count`**。`{"price":2,"count":20}` 表示 2 元买 20 个，总额就是 2 元。
- 该口径与接口 `totalIncome` 分毫不差（实测：1402.00 + 750.00 + 5332.00 = 7484.00）。

**人均弹幕** = `danmakusCount / interactionCount`（对齐 laplace.live），不是除以观看人数。

**时长** = `(stopDate - startDate) / 1000` 秒。

---

## 已知问题（实测踩坑记录）

| # | 问题 | 影响 | 应对 |
|---|---|---|---|
| 1 | `/live` 分页丢数据：`total=535` 时分页只能取到 303 条唯一记录，页内还有重复 | 用分页算流水会算错 | **全量拉取**，不传 `pageSize` |
| 2 | `type=2` 筛选失效：传 `type=2` 返回 `total=0` | 筛不出舰长记录 | 全量拉取后本地过滤 |
| 3 | `pageSize` 上限约 200，传 500 异常返回 35 条 | 分页异常 | 不超过 200 |
| 4 | `/swagger/v2/swagger.json` 含非法 JSON：11 处 `"kindValue": ,` | 无法直接解析 | 正则替换为 `"kindValue": null,` |
| 5 | `/rank/range` 参数格式未明，`range=30` 返回 400 | 无法用范围榜 | 用 `rank/month` 或 `rank/day` 替代 |
| 6 | `/rank/month` 返回顺序不严格按 `income` 降序 | 不能依赖顺序取 Top N | 自行排序 |
| 7 | v3 部分接口返回 msgpack 而非 JSON | `json.loads` 失败 | 用 msgpack 解码 |
| 8 | 域名 302 跳转 | `curl` 不加 `-L` 只能拿到跳转 | 跟随重定向 |

---

## 数据规模与覆盖

| 指标 | 数值（2026-10-18 实测） |
|---|---|
| 收录频道 | 30,119（`/site`）／47,056（`/channels` 含失效） |
| 有直播记录 | 28,921 |
| 总场次 | 4,581,089 |
| 累计弹幕 | 54.3 亿（`/channels` 求和）／88.2 亿（`/site`） |
| 累计流水 | 31.36 亿元 |
| 累计时长 | 1,766 万小时（约 2017 年） |

**数据来源**：该站靠社区投稿（「添加主播」）与用户挂客户端录制（「支持榜」）采集，不是官方数据。
**2026-01-24 曾发生服务器被黑，全部历史弹幕记录丢失**，站内有公告。
**覆盖不全**：没有记录/不更新的直播间就是没人录，新号小号大概率缺失。

---

## 使用边界

- 无书面授权，仅技术上开放（CORS `*`）。
- 数据涉及主播收益，属敏感信息。个人研究、内部使用风险低；**对外产品化或公开传播流水榜，请先联系 `i@danmakus.com`**。
- 控制频率：批量场景 1 请求/秒起步，不要并发轰炸。`rank/month count=30000` 这类重查询每次耗时 1~2 分钟，不要重复调用。
- 站点靠社区贡献维持，请勿滥用。
