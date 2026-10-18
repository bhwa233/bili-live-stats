# Danmakus API 使用说明

> 实测时间：2026-10-18　数据来源：[danmakus.com](https://danmakus.com)（弹幕站）
> 该站同时是 [laplace.live](https://laplace.live) 的后端数据源。

---

## 0. 基础信息

| 项 | 值 |
|---|---|
| API 入口 | `https://danmakus.com/api/v2`（同域，302 跳转到下者）<br>`https://ukamnads.icu/api/v2`（实际返回数据的域名） |
| 站点域名 | `https://danmakus.com`（前端 SPA，数据同源） |
| 协议 | HTTPS / REST / JSON（UTF-8） |
| 鉴权 | **无**（不需要 key、cookie、token） |
| CORS | `Access-Control-Allow-Origin: *`（浏览器端可直接跨域调用） |
| 服务端 | Caddy + Kestrel (.NET) |
| 官方文档 | **不存在**（`/api`、`/docs`、`/terms` 均 404） |

### 调用方式：普通 HTTP 客户端即可

**不需要**模拟浏览器、不需要特殊 header、不需要 cookie。普通 `requests` / `urllib` / `curl -L` 都能直接拿到数据。

唯一要处理的是**域名重定向**：

```
GET https://danmakus.com/api/v2/{path}
  → 302 Found
     Location: https://ukamnads.icu/api/v2/{path}
  → 200 JSON
```

`danmakus.com` 是别名入口，真正的数据由 `ukamnads.icu` 返回。两个域名都能用，让客户端跟随重定向即可：

```python
import requests
r = requests.get("https://danmakus.com/api/v2/channel?uId=2132180406", timeout=90)
# requests 默认跟随 302，r.json() 直接可用
```

```bash
curl -L "https://danmakus.com/api/v2/channel?uId=2132180406"
# curl 不加 -L 只会拿到 302
```

> 排查记录：本机曾出现请求返回 `000` 的情况，实测是**本地 HTTP_PROXY 环境变量指向了一个不可用的代理**所致，与服务端无关。若在你机器上遇到连不通，先检查 `HTTP_PROXY` / `HTTPS_PROXY` 或临时 `unset` 掉再试。

### 通用响应包装

```json
{ "code": 200, "message": "成功", "data": { ... } }
```

失败时：`{"code": 404, "message": "未找到", "data": null}`

---

## 1. 接口清单

| 接口 | 用途 | 单次体量 |
|---|---|---|
| `GET /api/v2/channels` | 全站所有频道概览 | **27 MB**（47,056 条） |
| `GET /api/v2/channel?uId={mid}` | 单主播信息 + **全部场次列表** | 0.4 ~ 1.7 MB |
| `GET /api/v2/live?liveId={uuid}` | 单场直播的逐条记录 | 1 KB ~ 7.2 MB |

---

## 2. `GET /api/v2/channels` —— 全站频道列表

无参数。一次返回全站所有收录频道（**不含场次明细**）。

```python
r = requests.get("https://danmakus.com/api/v2/channels", timeout=180)
channels = r.json()["data"]      # list，长度 47056
```

返回 `data` 为数组，每个元素是 `channel` 对象（字段见 §4）。

实测规模：47,056 条 / 27MB / 耗时约 28 秒。

---

## 3. `GET /api/v2/channel?uId={mid}` —— 主播 + 全部场次

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `uId` | int | 是 | B 站用户 mid（空间页 `space.bilibili.com/{mid}` 里的数字） |

返回结构：

```json
{
  "data": {
    "channel": { ... },        // 主播汇总，见 §4.1
    "lives":  [ { ... } ]       // 场次数组，见 §4.2
  }
}
```

**`lives` 返回该主播的全部历史场次**（不是最近 50 场）：

| 主播 | 累计场次 | lives 实际返回 |
|---|---|---|
| 明前奶绿 | 983 | 983（最早 2022-07） |
| 永雏塔菲 | 1,374 | 1,374（最早 2021-09） |
| 枝堇Sumire | 100 | 101 |

平均 **约 1.2 KB / 场**。注意每个场次对象里还嵌了 `versions` 数组（断流分段记录），是体积偏大的主因，实际只用外层字段时可以忽略。

---

## 4. 字段说明

### 4.1 `channel` 对象

| 字段 | 类型 | 含义 |
|---|---|---|
| `uId` | int | B 站 mid |
| `uName` | str | 主播名 |
| `roomId` | int | 直播间号 |
| `faceUrl` | str | 头像 URL |
| `isLiving` | bool | 当前是否在播 |
| `title` | str | 最近一场的标题 |
| `fansCount` | int | 粉丝数 |
| `followCount` | int | 关注数 |
| `totalLiveCount` | int | 累计场次 |
| `totalLiveSecond` | int | 累计直播时长（秒） |
| `totalDanmakuCount` | int | 累计弹幕数 |
| `totalIncome` | float | **累计流水（元）** |
| `lastLiveDate` | int | 最近一场开始时间（ms 时间戳） |
| `lastLiveIncome` | float | 最近一场流水（元） |
| `lastLiveDanmakuCount` | int | 最近一场弹幕数 |
| `lastUpdateStatAt` | int | 统计最后更新时间（ms） |
| `addDate` | str | 收录进本站的时间 |
| `isDeleted` | bool | 是否已删除/失效 |
| `tags` | array | 标签（常为空） |

### 4.2 `lives[]` 单个场次

| 字段 | 类型 | 含义 |
|---|---|---|
| `liveId` | str | **场次唯一 ID（UUID），拉明细必用** |
| `title` | str | 场次标题 |
| `startDate` | int | 开播时间（ms） |
| `stopDate` | int | 下播时间（ms） |
| `totalIncome` | float | **本场流水（元）** |
| `watchCount` | int | **本场观看人数** |
| `danmakusCount` | int | 本场弹幕数 |
| `interactionCount` | int | 互动数 |
| `payCount` | int | 付费人数 |
| `likeCount` | int | 点赞数 |
| `maxOnlineCount` | int | 峰值在线人数 |
| `commentCount` | int | 评论数 |
| `parentArea` | str | 一级分区（如"虚拟主播"） |
| `area` | str | 二级分区（如"虚拟日常"） |
| `coverUrl` | str | 封面图 |
| `isFinish` | bool | 是否已结束 |
| `isFull` | bool | 是否完整录制 |
| `isMerged` | bool | 是否已合并分段 |
| `versions` | array | 分段/断流版本记录 |

> 计算时长：`(stopDate - startDate) / 1000` 秒。
> 同一主播同一天可能出现多场，用 `startDate` 排序即可。

---

## 5. `GET /api/v2/live?liveId={uuid}` —— 单场逐条记录

| 参数 | 类型 | 说明 |
|---|---|---|
| `liveId` | str | 必填，取自 `lives[].liveId` |
| `type` | int | 可选，按记录类型过滤（**有坑，见 §6**） |
| `pageNum` | int | 可选，页码，从 1 开始 |
| `pageSize` | int | 可选，每页条数；不传则返回全部 |

返回结构：

```json
{
  "data": {
    "total": 80014,          // 总记录数
    "pageNum": 1,
    "pageSize": 10,
    "hasMore": true,
    "data": {
      "channel": { ... },
      "live":    { ... },     // 同 §4.2 的场次对象
      "danmakus": [ ... ]     // 逐条记录，见下表
    }
  }
}
```

### `danmakus[]` 单条记录

| 字段 | 类型 | 含义 |
|---|---|---|
| `uId` | int | 发送者 mid |
| `uName` | str | 发送者昵称 |
| `type` | int | 记录类型，见下表 |
| `sendDate` | int | 发送时间（ms） |
| `message` | str | 内容（弹幕文本 / SC 内容 / 礼物名） |
| `price` | float | **金额（元）**，仅付费记录有 |
| `count` | int | 数量（礼物个数、舰长月数） |

### `type` 编码

| type | 含义 | 有 price | 实测条数（样例场） |
|---|---|---|---|
| `0` | 普通弹幕 | 否 | 41,425 |
| `1` | **礼物**（含粉丝团灯牌等小额） | 是 | 535 |
| `2` | **大航海 / 舰长** | 是 | 5 |
| `3` | **醒目留言 SC** | 是 | 178 |
| `4` | 入场 / 看过 | 否 | 37,868 |

**流水校验（重要）**：`type 1 + 2 + 3` 的 `price` 之和 **等于** 场次的 `totalIncome`。

实测样例：礼物 1,402.00 + 舰长 750.00 + SC 5,332.00 = **7,484.00** = 接口 `totalIncome`，分毫不差。

---

## 6. 已知坑（务必注意）

### 6.1 `type=2` 筛选失效

`type=2` 传进去会返回 `total=0`，**筛不出舰长记录**（服务端 bug）。而全量返回里明明有 `type=2` 的数据。

| 参数 | 结果 |
|---|---|
| `type=0` / `type=1` / `type=3` / `type=4` | ✅ 正常过滤 |
| `type=2` | ❌ total=0 |
| `type=1,2,3` | ❌ 只按最后一个生效（返回 178 = SC 数） |

**绕法一（推荐）**：只拉 `type=1` 和 `type=3`，舰长金额用总流水反推：

```
舰长金额 = totalIncome - (礼物总额 + SC总额)
```

**绕法二**：全量拉取（7.2MB）后本地过滤 `type==2`。

### 6.2 全量明细很贵

一场大主播 8 万条记录 ≈ 7.2MB。全场次明细全站 ≈ 1TB。**能分页就分页，能按 type 筛就筛。**

### 6.3 `versions` 冗余

`lives[].versions` 会把整场信息再嵌一层，占掉不少体积。只需要核心指标时不解析它即可。

### 6.4 无 SLA、无文档

接口随时可能变更或加限制。**首次拉到数据就落库，不要把它当唯一数据源。**

---

## 7. 代码示例

### 7.1 拉单个主播的全部场次

```python
import requests

r = requests.get("https://danmakus.com/api/v2/channel?uId=2132180406", timeout=90)
d = r.json()["data"]
c = d["channel"]
print(c["uName"], c["totalLiveCount"], c["totalIncome"])

for lv in d["lives"]:
    dur = (lv["stopDate"] - lv["startDate"]) / 1000 / 3600
    print(lv["startDate"], f'{dur:.1f}h', lv["totalIncome"], lv["watchCount"])
```

### 7.2 拉单场流水明细（只取付费记录）

```python
live_id = "1c8b7094-5c3c-401f-aaef-6c61ec493296"

def collect(live_id, t):
    out, page = [], 1
    while True:
        r = requests.get(f"https://danmakus.com/api/v2/live?liveId={live_id}"
                         f"&type={t}&pageNum={page}&pageSize=500", timeout=60)
        d = r.json()["data"]
        out += d["data"]["danmakus"]
        if not d["hasMore"]:
            return out
        page += 1

gift = collect(live_id, 1)   # 礼物
sc   = collect(live_id, 3)   # SC
print("礼物", sum(x["price"] for x in gift),
      "SC", sum(x["price"] for x in sc))
```

### 7.3 全站频道快照

```python
r = requests.get("https://danmakus.com/api/v2/channels", timeout=180)
rows = [{
    "mid": c["uId"], "name": c["uName"], "fans": c["fansCount"],
    "lives": c["totalLiveCount"], "income": c["totalIncome"],
} for c in r.json()["data"]]
```

---

## 8. 全站数据规模（实测汇总）

| 指标 | 数值 |
|---|---|
| 收录频道 | 47,056（有直播记录 28,921，占 61.5%） |
| 总场次 | 4,581,089 |
| 总弹幕 | 5,428,031,582（54.3 亿） |
| 总时长 | 17,667,829 小时（≈2017 年） |
| 总流水 | 3,136,331,988 元（31.36 亿） |
| 场均弹幕 | 1,185 |
| 场均流水 | 685 元 |

存储体量分层估算：

| 层级 | 内容 | 体量 | 请求次数 |
|---|---|---|---|
| 主播级 | 每个主播累计值 | 27 MB | 1 |
| 场次级 | 每场流水/观看/弹幕/时长 | ≈5.5 GB | 47,056 |
| 逐条明细 | 每条弹幕/礼物/SC/舰长 | ≈1 TB（104.8 亿条） | 4,581,089 |

---

## 9. 做一个 laplace 同款统计页需要什么

`laplace.live/stats/{mid}` 的每个模块，对应的取数方式：

| 页面模块 | 数据来源 | 计算方式 |
|---|---|---|
| 头部：主播名 / 头像 / 粉丝 | `channel` | 直接取 |
| 总时长 | `channel.totalLiveSecond` | 格式化为 `H:MM:SS` |
| 场均时长 | — | `totalLiveSecond / totalLiveCount` |
| 总弹幕 | `channel.totalDanmakuCount` | 直接取 |
| 场均弹幕 | — | `totalDanmakuCount / totalLiveCount` |
| 流水曲线 | `lives[].totalIncome` | 按 `startDate` 排序出点 |
| 观看曲线 | `lives[].watchCount` | 同上 |
| 互动曲线 | `lives[].interactionCount` | 同上 |
| 弹幕曲线 | `lives[].danmakusCount` | 同上 |
| 人均弹幕 | — | `danmakusCount / watchCount` |
| 场次列表 | `lives[]` | 按 `startDate` 倒序 |
| 单场下钻（礼物/SC/舰长构成） | `/live?liveId=` | 按 `type` 分组求和 |

**结论：`channel` 一个接口就能喂满整个页面，`/live` 只用于单场下钻。**

---

## 10. 使用边界

- 无书面授权，仅"技术上开放"（CORS `*`）。数据涉及主播收益，属敏感信息。
- 个人研究、内部使用风险低；**对外产品化或公开传播流水榜，请先联系 `i@danmakus.com` 说明用途。**
- 控制频率：不要分钟级轮询，不要并发轰炸。批量抓取建议 1 请求/秒起步。
- 该站靠社区投稿（"添加主播"）和用户挂客户端维持，属于用爱发电，请勿滥用。
