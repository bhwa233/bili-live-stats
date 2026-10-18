---
name: bili-live-stats
description: 查询 B 站主播（虚拟主播/VUP/VTuber/普通主播）的直播数据。支持查询某主播的每场直播流水、观看人数、弹幕数、互动数、付费人数、直播时长，单场直播的收入构成（礼物/醒目留言SC/舰长拆分）与打赏排行，以及全站主播的流水榜/弹幕榜/场次榜/粉丝榜。当用户询问某个 B 站主播直播赚了多少钱、某场直播收入多少、直播数据统计、流水趋势、或需要按主播/时间维度做直播数据汇总时使用。数据源为第三方监控站 danmakus.com，无需登录与 API key。
agent_created: true
---

# B站主播直播数据查询

通过 danmakus.com 的公开接口查询 B 站主播的场次级直播数据。该站长期监控并记录了 4.7 万个频道、458 万场直播，覆盖虚拟主播与部分其他分区。

**不提供**：B 站官方数据、实时弹幕流、视频数据。仅提供已被该站监控到的直播场次数据。

## 环境

脚本零依赖，仅用 Python 标准库。用任意可用的 Python 3.9+ 执行：

```bash
python scripts/query.py <子命令> [参数]
```

在 Windows 上若中文输出乱码，先 `set PYTHONIOENCODING=utf-8`。

## 命令

| 命令 | 用途 | 典型耗时 |
|---|---|---|
| `site` | **站点宏观指标**（收录频道/在播/累计弹幕/采集速率） | 1s |
| `month <year> <month> [N]` | **月度流水榜**，`--area 虚拟主播` 筛分区，`--total` 全量求和 | 5s；全量 1~2min |
| `info <mid>` | 主播概览（累计场次/总时长/总流水/场均） | 2~5s |
| `lives <mid> [N]` | 最近 N 场明细（默认 20），支持 `--since` / `--until` | 2~5s |
| `live <liveId>` | 单场收入构成 + 打赏 Top10 | 20~30s |
| `rank [metric] [N]` | 全站榜单（基于全站快照），metric = income/danmaku/lives/fans | 首次约 2min，之后 1~2s |
| `find <关键词>` | 按昵称搜 mid | 首次同上，之后 1~2s |

全局加 `--json` 输出结构化数据，便于二次处理。

### 宏观与月度统计

站点有现成的宏观接口和月度榜，**不要用抽样估算**：

```bash
python scripts/query.py site                    # 全站总量
python scripts/query.py month 2026 10           # 本月流水榜 Top30
python scripts/query.py month 2026 10 20 --area 虚拟主播
python scripts/query.py month 2026 10 --area 虚拟主播 --total   # 精确求和
```

`month --total` 会拉 `count=30000` 拿回全部有流水的频道再求和，是**精确值**（实测 2026-10 全站 8,160.6 万、虚拟区 2,396.9 万，占 29.4%）。

> 官方 Swagger 文档：<https://ukamnads.icu/swagger>（86 个端点）。完整端点清单、字段表、参数说明见 `references/api.md`。

## 常用组合

查询某主播最近的表现：

```bash
python scripts/query.py info 2132180406
python scripts/query.py lives 2132180406 20
```

查某个时间段：

```bash
python scripts/query.py lives 2132180406 100 --since 2026-09-01 --until 2026-09-30
```

拆解某场直播的钱从哪来（`liveId` 通过 `--json` 获取）：

```bash
python scripts/query.py lives 2132180406 5 --json | grep liveId
python scripts/query.py live 1c8b7094-5c3c-401f-aaef-6c61ec493296
```

按名字找人、看全站排名：

```bash
python scripts/query.py find 奶绿
python scripts/query.py rank income 30
```

## 数据口径（必须遵守）

**流水金额**：`type` 为 1（礼物）、2（舰长）、3（SC）的 `price` 直接相加。

- `price` 已经是该条记录的总金额，**不要再乘 `count`**。例如 `{"price":2,"count":20}` 表示 2 元买 20 个小花花，总额就是 2 元。
- 此口径与接口返回的 `totalIncome` 完全一致，可作为校验依据。

**人均弹幕**：用 `danmakusCount / interactionCount`（对齐 laplace.live 的口径），不是除以观看人数。

**时长**：`(stopDate - startDate) / 1000` 秒。同一主播同一天可能有多场，按 `startDate` 区分。

## 已知接口缺陷（不要踩）

1. **分页会丢数据**：`/live` 接口 `total=535` 时分页只能取到 303 条唯一记录，页内还有重复。统计流水**必须全量拉取**（不传 `pageSize`），脚本已按此实现。
2. **`type=2` 筛选失效**：传 `type=2` 返回 `total=0`，筛不出舰长。脚本改为全量拉取后本地过滤。
3. **`pageSize` 上限约 200**：传 500 会异常返回 35 条。仅在快速预览时使用分页，且不要超过 200。
4. **域名要跟随重定向**：`danmakus.com/api/v2/*` 会 302 跳到 `ukamnads.icu`，普通 HTTP 客户端跟随即可，无需特殊处理。
5. **Swagger spec 本身是坏 JSON**：`/swagger/v2/swagger.json` 有 11 处 `"kindValue": ,`，直接 `json.loads` 会失败，需正则替换为 `"kindValue": null,`。
6. **`rank/month` 返回顺序不按 `income` 降序**：需要 Top N 时自行排序，不要依赖接口顺序。
7. **`rank/range` 参数格式未明**：`range=30` 返回 400，用 `rank/month` 或 `rank/day` 替代。

## 注意事项

- **覆盖范围有限**：只包含被该站监控/投稿收录的频道。查不到不代表主播没播过；新主播、小主播可能缺失。
- **数据非实时**：统计有延迟，通常滞后数小时到一天。
- **首次榜单查询慢**：`rank` / `find` 需下载 27MB 全站快照并缓存到 `~/.cache/bili-live-stats/channels.json`（24 小时有效）。非必要不要频繁 `--refresh`。
- **无官方授权**：接口无文档、无使用条款，技术上开放（CORS 全开）但无书面许可。个人研究与小范围使用风险低；**对外产品化或公开传播流水榜前，先联系 `i@danmakus.com` 说明用途**。
- **控制频率**：批量查询建议 1 请求/秒，不要并发轰炸。该站靠社区贡献维持运行。

接口字段与完整参数说明见 `references/api.md`。
