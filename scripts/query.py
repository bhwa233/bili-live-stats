#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站主播直播数据查询 CLI

数据源：danmakus.com（第三方监控站，非 B 站官方）
无需登录、无需 API key。零第三方依赖，仅用标准库。

用法：
    python query.py info  <mid>                 主播概览
    python query.py lives <mid> [N]             最近 N 场（默认 20）
    python query.py live  <liveId>              单场收入构成 + 打赏排行
    python query.py rank  [metric] [N]          全站榜单
    python query.py find  <关键词>              按昵称搜主播

全局选项：
    --json     输出原始 JSON（便于二次处理）
    --since YYYY-MM-DD / --until YYYY-MM-DD   按日期过滤场次

数据口径（实测校准）：
    - 流水 = 礼物(type=1) + 舰长(type=2) + SC(type=3) 的 price 之和
    - price 字段本身就是该条记录的总金额，**不要**再乘 count
    - 该口径与接口返回的 totalIncome 分毫不差
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://danmakus.com/api/v2'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
CACHE_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'bili-live-stats')
CHANNELS_CACHE = os.path.join(CACHE_DIR, 'channels.json')
CACHE_TTL = 86400          # /channels 快照缓存 24 小时
TYPE_NAME = {1: '礼物', 2: '舰长', 3: 'SC'}


# ---------------------------------------------------------------- 基础设施

def _out(text=''):
    try:
        sys.stdout.write(text + '\n')
    except UnicodeEncodeError:
        sys.stdout.write(text.encode('utf-8', 'replace').decode('utf-8') + '\n')


def fetch(url, timeout=180, retry=3):
    """GET 并解析 JSON。自动跟随 302（urllib 默认行为）。"""
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:                       # noqa: BLE001
            last = e
            if i < retry - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f'请求失败: {url}\n{last}')


def api(path, timeout=180):
    d = fetch(API + path, timeout=timeout)
    if d.get('code') != 200:
        raise RuntimeError(f"接口返回 {d.get('code')}: {d.get('message')}")
    return d.get('data')


def ts(ms):
    if not ms:
        return '-'
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M')


def day(ms):
    return ts(ms)[:10]


def dur(sec):
    sec = max(0, int(sec or 0))
    return f'{sec // 3600}h{sec % 3600 // 60:02d}m'


def num(n):
    return '-' if n is None else f'{int(n):,}'


def money(v):
    return f'{float(v or 0):,.2f}'


def pct(a, b):
    return f'{(a / b * 100):.1f}%' if b else '-'


def parse_day(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d').timestamp() * 1000


# ---------------------------------------------------------------- 全站快照

def channels_snapshot(force=False):
    """全站频道列表（47k 条 / 27MB / 约 28s）。缓存 24h。"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not force and os.path.exists(CHANNELS_CACHE):
        age = time.time() - os.path.getmtime(CHANNELS_CACHE)
        if age < CACHE_TTL:
            with open(CHANNELS_CACHE, encoding='utf-8') as f:
                return json.load(f)
    _out('· 正在拉取全站频道快照（约 27MB，首次需 30 秒左右）...')
    data = api('/channels', timeout=300)
    with open(CHANNELS_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return data


# ---------------------------------------------------------------- 命令实现

def cmd_info(args):
    d = api(f'/channel?uId={args.mid}', timeout=120)
    c = d['channel']
    lives = d.get('lives') or []
    if args.json:
        print(json.dumps(c, ensure_ascii=False, indent=2))
        return

    n = c.get('totalLiveCount') or 1
    sec = c.get('totalLiveSecond') or 0
    dm = c.get('totalDanmakuCount') or 0
    income = float(c.get('totalIncome') or 0)

    _out(f"{c['uName']}  (mid={c['uId']}, room={c['roomId']})")
    _out(f"粉丝 {num(c.get('fansCount'))} · 累计 {num(n)} 场 · "
         f"累计流水 {income / 1e4:,.2f} 万元 · 累计弹幕 {dm / 1e4:,.1f} 万")
    _out(f"总时长 {sec / 3600:,.0f} 小时 · 场均 {dur(sec / n)} · "
         f"场均弹幕 {num(round(dm / n))} · 场均流水 {num(round(income / n))} 元")
    if lives:
        last = lives[0]
        _out(f"最近一场 {ts(last.get('startDate'))}  {last.get('title', '')[:24]}  "
             f"{money(last.get('totalIncome'))} 元")


def cmd_lives(args):
    d = api(f'/channel?uId={args.mid}', timeout=120)
    c = d['channel']
    rows = [x for x in (d.get('lives') or []) if x.get('isFinish')]
    rows.sort(key=lambda x: x.get('startDate') or 0, reverse=True)

    if args.since:
        lo = parse_day(args.since)
        rows = [x for x in rows if (x.get('startDate') or 0) >= lo]
    if args.until:
        hi = parse_day(args.until) + 86400000
        rows = [x for x in rows if (x.get('startDate') or 0) < hi]

    rows = rows[:args.n]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    _out(f"{c['uName']} · 最近 {len(rows)} 场")
    _out('-' * 92)
    _out(f"{'开播时间':17s}{'时长':>7s}{'观看':>9s}{'弹幕':>9s}{'付费':>7s}{'流水(元)':>11s}  标题")
    total = 0.0
    for r in rows:
        inc = float(r.get('totalIncome') or 0)
        total += inc
        sec = (r.get('stopDate', 0) - r.get('startDate', 0)) / 1000
        _out(f"{ts(r.get('startDate')):17s}{dur(sec):>7s}"
             f"{num(r.get('watchCount')):>9s}{num(r.get('danmakusCount')):>9s}"
             f"{num(r.get('payCount')):>7s}{money(inc):>11s}  {(r.get('title') or '')[:26]}")
    _out('-' * 92)
    _out(f"合计 {len(rows)} 场 · 流水 {money(total)} 元 · 场均 {money(total / max(len(rows), 1))} 元")


def cmd_live(args):
    # 必须全量拉取：分页接口会丢记录（total=535 时分页只能取到 303 条唯一数据）
    d = api(f'/live?liveId={args.live_id}', timeout=180)
    inner = d.get('data') or {}
    lv = inner.get('live') or {}
    records = inner.get('danmakus') or []

    amt, cnt = {}, {}
    payer = {}
    for x in records:
        t = x.get('type')
        if t not in TYPE_NAME:
            continue
        p = float(x.get('price') or 0)
        amt[t] = amt.get(t, 0) + p
        cnt[t] = cnt.get(t, 0) + 1
        who = x.get('uName') or str(x.get('uId'))
        payer[who] = payer.get(who, 0) + p

    total = sum(amt.values())
    if args.json:
        print(json.dumps({
            'liveId': args.live_id,
            'title': lv.get('title'),
            'startDate': lv.get('startDate'),
            'stopDate': lv.get('stopDate'),
            'totalIncome': lv.get('totalIncome'),
            'watchCount': lv.get('watchCount'),
            'danmakusCount': lv.get('danmakusCount'),
            'interactionCount': lv.get('interactionCount'),
            'payCount': lv.get('payCount'),
            'breakdown': {TYPE_NAME[t]: {'count': cnt[t], 'amount': round(amt[t], 2)}
                          for t in TYPE_NAME if cnt.get(t)},
            'computed_total': round(total, 2),
            'top_payers': [{'name': k, 'amount': round(v, 2)}
                           for k, v in sorted(payer.items(), key=lambda kv: -kv[1])[:10]],
        }, ensure_ascii=False, indent=2))
        return

    sec = (lv.get('stopDate', 0) - lv.get('startDate', 0)) / 1000
    _out(f"场次：{lv.get('title', '')}")
    _out(f"{ts(lv.get('startDate'))} → {ts(lv.get('stopDate'))[11:]}  ({dur(sec)})  "
         f"{lv.get('parentArea', '')}/{lv.get('area', '')}")
    _out(f"观看 {num(lv.get('watchCount'))} · 弹幕 {num(lv.get('danmakusCount'))} · "
         f"互动 {num(lv.get('interactionCount'))} · 付费人数 {num(lv.get('payCount'))} · "
         f"峰值在线 {num(lv.get('maxOnlineCount'))}")
    _out('')
    _out(f"流水合计 {money(total)} 元")
    for t in (1, 3, 2):
        if cnt.get(t):
            _out(f"  {TYPE_NAME[t]:4s} {cnt[t]:>5d} 笔  {money(amt[t]):>12s} 元   {pct(amt[t], total)}")
    if lv.get('totalIncome') is not None:
        diff = float(lv['totalIncome']) - total
        flag = '一致' if abs(diff) < 0.01 else f'差异 {diff:+.2f}'
        _out(f"  （接口 totalIncome={money(lv['totalIncome'])} → {flag}）")

    top = sorted(payer.items(), key=lambda kv: -kv[1])[:10]
    if top and top[0][1] > 0:
        _out('')
        _out('打赏 Top：')
        for i, (name, v) in enumerate(top, 1):
            _out(f"  {i:>2d}. {name[:18]:20s}{money(v):>12s} 元")


def cmd_rank(args):
    ch = channels_snapshot(args.refresh)
    metric = args.metric
    key = {
        'income': 'totalIncome',
        'watch': 'lastLiveDanmakuCount',   # 占位，实际用下面分支
        'danmaku': 'totalDanmakuCount',
        'lives': 'totalLiveCount',
        'fans': 'fansCount',
    }.get(metric, 'totalIncome')

    rows = [x for x in ch if (x.get('totalLiveCount') or 0) > 0]
    rows.sort(key=lambda x: (x.get(key) or 0), reverse=True)
    rows = rows[:args.n]

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    label = {'income': '累计流水(元)', 'danmaku': '累计弹幕', 'lives': '场次',
             'fans': '粉丝数'}.get(metric, metric)
    _out(f'全站 Top {len(rows)} · 按{label}')
    _out('-' * 78)
    _out(f"{'#':>4s}  {'主播':24s}{'流水(万)':>12s}{'场次':>8s}{'弹幕(万)':>11s}{'粉丝':>12s}")
    for i, x in enumerate(rows, 1):
        _out(f"{i:>4d}  {(x.get('uName') or '')[:22]:24s}"
             f"{float(x.get('totalIncome') or 0) / 1e4:>12,.1f}"
             f"{num(x.get('totalLiveCount')):>8s}"
             f"{float(x.get('totalDanmakuCount') or 0) / 1e4:>11,.0f}"
             f"{num(x.get('fansCount')):>12s}")


def cmd_find(args):
    ch = channels_snapshot(args.refresh)
    kw = args.keyword.lower()
    hits = [x for x in ch if kw in (x.get('uName') or '').lower()]
    hits.sort(key=lambda x: -(x.get('fansCount') or 0))
    hits = hits[:args.n]

    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return
    if not hits:
        _out('没有匹配的主播（该站只收录被投稿/监控过的频道）')
        return
    _out(f'匹配 {len(hits)} 个：')
    for x in hits:
        _out(f"  {x['uName'][:24]:26s} mid={x['uId']:<12} "
             f"粉丝{num(x.get('fansCount')):>10s} 场次{num(x.get('totalLiveCount')):>6s} "
             f"流水{float(x.get('totalIncome') or 0) / 1e4:>8,.1f}万")


# ---------------------------------------------------------------- 入口

def main():
    p = argparse.ArgumentParser(description='B站主播直播数据查询（数据源 danmakus.com）')
    p.add_argument('--json', action='store_true', help='输出原始 JSON')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('info', help='主播概览')
    s.add_argument('mid')
    s.set_defaults(func=cmd_info)

    s = sub.add_parser('lives', help='场次列表')
    s.add_argument('mid')
    s.add_argument('n', nargs='?', type=int, default=20)
    s.add_argument('--since')
    s.add_argument('--until')
    s.set_defaults(func=cmd_lives)

    s = sub.add_parser('live', help='单场收入构成')
    s.add_argument('live_id')
    s.set_defaults(func=cmd_live)

    s = sub.add_parser('rank', help='全站榜单')
    s.add_argument('metric', nargs='?', default='income',
                   choices=['income', 'danmaku', 'lives', 'fans'])
    s.add_argument('n', nargs='?', type=int, default=30)
    s.add_argument('--refresh', action='store_true', help='强制刷新快照')
    s.set_defaults(func=cmd_rank)

    s = sub.add_parser('find', help='搜索主播')
    s.add_argument('keyword')
    s.add_argument('n', nargs='?', type=int, default=10)
    s.add_argument('--refresh', action='store_true')
    s.set_defaults(func=cmd_find)

    args = p.parse_args()
    if args.cmd == 'find' and not hasattr(args, 'refresh'):
        args.refresh = False
    try:
        args.func(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:                            # noqa: BLE001
        _out(f'错误：{e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
