#!/usr/bin/env python3
"""
每日新闻简报 — 自动抓取国内外要闻，通过 Server酱 推送到微信。
用法: python daily_news.py
配合 GitHub Actions 每日定时运行。
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import List, Dict

import feedparser
import requests

# ============================================================
# 路径
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "news_log.txt")


def log(msg: str):
    """写日志"""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ============================================================
# 配置
# ============================================================
def load_config() -> dict:
    """加载配置：优先 config.json，否则从环境变量读取"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    # GitHub Actions 模式：从环境变量读取
    return {
        "max_items": int(os.environ.get("MAX_ITEMS", "20")),
        "send_key": os.environ.get("SEND_KEY", ""),
    }


# ============================================================
# 新闻源
# ============================================================

RSS_SOURCES: List[dict] = [
    {"name": "新华网-时政", "url": "http://www.xinhuanet.com/politics/news_politics.xml", "category": "国内"},
    {"name": "人民网-时政", "url": "http://www.people.com.cn/rss/politics.xml", "category": "国内"},
    {"name": "环球网", "url": "https://www.huanqiu.com/rss/news.xml", "category": "国内"},
    {"name": "BBC 中文", "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "category": "国际"},
    {"name": "德国之声中文", "url": "https://rss.dw.com/rss/rss-chi-all", "category": "国际"},
    {"name": "FT 中文网", "url": "https://www.ftchinese.com/rss/feed", "category": "国际"},
]

WEB_SOURCES: List[dict] = [
    {"name": "澎湃新闻", "url": "https://www.thepaper.cn/", "category": "国内"},
    {"name": "新浪新闻", "url": "https://news.sina.com.cn/", "category": "国内"},
    {"name": "参考消息", "url": "https://www.cankaoxiaoxi.com/", "category": "国际"},
]


# ============================================================
# 新闻抓取
# ============================================================

def fetch_rss(source: dict) -> List[dict]:
    """从单个 RSS 源抓取新闻"""
    items = []
    try:
        feed = feedparser.parse(source["url"])
        if feed.bozo and not feed.entries:
            return items

        for entry in feed.entries[:15]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            if len(summary) > 200:
                summary = summary[:200] + "…"

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "source": source["name"],
                    "category": source["category"],
                })
    except Exception as e:
        log(f"  ⚠️ RSS 失败 [{source['name']}]: {e}")
    return items


def fetch_web(source: dict) -> List[dict]:
    """从网页抓取新闻标题"""
    items = []
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(source["url"], headers=headers, timeout=15)
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if len(title) < 10 or len(title) > 100 or title in seen:
                continue
            href = a["href"]
            if href.startswith("/"):
                href = requests.compat.urljoin(source["url"], href)
            seen.add(title)
            items.append({
                "title": title, "link": href,
                "summary": "", "source": source["name"], "category": source["category"],
            })
            if len(items) >= 15:
                break
    except Exception as e:
        log(f"  ⚠️ 网页失败 [{source['name']}]: {e}")
    return items


def fetch_all_news() -> List[dict]:
    """从所有源抓取新闻并去重"""
    all_items: List[dict] = []
    seen: set = set()

    for source in RSS_SOURCES:
        log(f"📡 RSS: {source['name']}...")
        for item in fetch_rss(source):
            key = item["title"][:30]
            if key not in seen:
                seen.add(key)
                all_items.append(item)

    domestic_n = len([i for i in all_items if i["category"] == "国内"])
    intl_n = len([i for i in all_items if i["category"] == "国际"])

    if domestic_n < 5 or intl_n < 5:
        for source in WEB_SOURCES:
            log(f"🌐 网页: {source['name']}...")
            for item in fetch_web(source):
                key = item["title"][:30]
                if key not in seen:
                    seen.add(key)
                    all_items.append(item)
                    if item["category"] == "国内":
                        domestic_n += 1
                    else:
                        intl_n += 1

    return all_items


# ============================================================
# 新闻筛选
# ============================================================

KEYWORDS = {
    "国内": [
        # 核心人物与机构
        "习近平", "李强", "国务院", "人大", "政协", "中央",
        # 法律
        "法律", "法治", "司法", "最高人民法院", "最高人民检察院",
        "民法典", "刑法", "宪法", "修法", "立法",
        # 经济
        "经济", "GDP", "增长", "房地产", "楼市", "股市", "A股",
        "就业", "失业", "消费", "降息", "降准", "通胀",
        # 两岸与外交
        "台湾", "香港", "澳门", "南海", "钓鱼岛", "中俄", "中美",
        # 科技
        "科技", "芯片", "AI", "人工智能", "华为", "5G", "航天",
        # 民生
        "高考", "养老金", "医保", "房价", "食品安全",
        # 军事
        "军事", "国防", "解放军",
    ],
    "国际": [
        # 大国
        "美国", "特朗普", "拜登", "白宫", "国会",
        "俄罗斯", "普京", "乌克兰", "北约",
        "欧盟", "中国", "日本", "韩国", "朝鲜", "印度",
        # 冲突与安全
        "战争", "冲突", "停火", "制裁", "核", "导弹",
        # 经济
        "贸易", "关税", "美联储", "加息", "降息", "通胀",
        "全球经济", "供应链", "石油",
        # 科技
        "AI", "人工智能", "芯片", "SpaceX", "太空",
        # 国际组织
        "联合国", "WHO", "WTO", "G7", "G20",
        # 气候与环境
        "气候", "减排", "碳",
        # 重大事件
        "选举", "峰会", "协议", "谈判", "警告",
    ],
}

# 最低分数线：低于此分的新闻不入选
MIN_SCORE = 2


def score_news(item: dict) -> int:
    score = 0
    for kw in KEYWORDS.get(item["category"], []):
        if kw in item["title"]:
            score += 5
    if 15 <= len(item["title"]) <= 50:
        score += 3
    if item.get("summary"):
        score += 2
    return score


def select_top_news(items: List[dict], total: int = 20) -> List[dict]:
    """
    筛选最重要新闻，国内国际各约一半。
    只选有质量的（分数 ≥ MIN_SCORE），宁缺毋滥。
    """
    domestic = sorted(
        [i for i in items if i["category"] == "国内" and score_news(i) >= MIN_SCORE],
        key=score_news, reverse=True,
    )
    international = sorted(
        [i for i in items if i["category"] == "国际" and score_news(i) >= MIN_SCORE],
        key=score_news, reverse=True,
    )

    # 目标各 10 条，但根据实际情况灵活调整
    half = total // 2
    dom_n = min(len(domestic), half)
    intl_n = min(len(international), half)

    # 如果一方不够，另一方补上
    if dom_n < half:
        intl_n = min(len(international), total - dom_n)
    if intl_n < half:
        dom_n = min(len(domestic), total - intl_n)

    selected = domestic[:dom_n] + international[:intl_n]
    selected.sort(key=score_news, reverse=True)
    return selected


# ============================================================
# 生成内容
# ============================================================

def format_markdown(items: List[dict]) -> str:
    """生成 Markdown 格式的新闻简报（Server酱支持）"""
    today = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][datetime.now().weekday()]

    domestic = [i for i in items if i["category"] == "国内"]
    international = [i for i in items if i["category"] == "国际"]

    lines = [
        f"## 📰 每日新闻简报",
        f"**{today} 星期{weekday}**\n",
    ]

    if domestic:
        lines.append("### 🇨🇳 国内要闻\n")
        for i, item in enumerate(domestic, 1):
            line = f"{i}. [{item['title']}]({item['link']}) — *{item['source']}*"
            lines.append(line)
            if item.get("summary"):
                lines.append(f"   > {item['summary']}")
            lines.append("")

    if international:
        lines.append("### 🌍 国际要闻\n")
        for i, item in enumerate(international, 1):
            line = f"{i}. [{item['title']}]({item['link']}) — *{item['source']}*"
            lines.append(line)
            if item.get("summary"):
                lines.append(f"   > {item['summary']}")
            lines.append("")

    lines.append("---")
    lines.append(f"🤖 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)


# ============================================================
# Server酱 推送
# ============================================================

def push_wechat(config: dict, content: str):
    """通过 Server酱 推送到微信"""
    send_key = config.get("send_key", "")
    if not send_key:
        log("❌ 未配置 Server酱 SendKey")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://sctapi.ftqq.com/{send_key}.send"

    try:
        resp = requests.post(url, data={
            "title": f"📰 每日新闻简报 — {today}",
            "desp": content,
        }, timeout=30)

        result = resp.json()
        if result.get("code") == 0:
            log("✅ 已推送到微信")
        else:
            log(f"❌ 推送失败: {result}")
            sys.exit(1)
    except Exception as e:
        log(f"❌ 推送异常: {e}")
        sys.exit(1)


# ============================================================
# 主流程
# ============================================================

def main():
    log("=" * 50)
    log("📰 开始生成每日新闻简报")

    config = load_config()
    max_items = config.get("max_items", 7)

    # 1. 抓取
    log("🔍 正在抓取新闻...")
    all_news = fetch_all_news()
    log(f"📊 共抓取 {len(all_news)} 条候选")

    if not all_news:
        log("❌ 未能获取任何新闻，请检查网络连接")
        sys.exit(1)

    # 2. 筛选
    selected = select_top_news(all_news, max_items)
    dom_n = len([i for i in selected if i["category"] == "国内"])
    intl_n = len([i for i in selected if i["category"] == "国际"])
    log(f"✨ 已筛选 {len(selected)} 条（国内 {dom_n} + 国际 {intl_n}）")

    for item in selected:
        log(f"  · [{item['category']}] {item['title'][:50]} — {item['source']}")

    # 3. 生成 Markdown
    content = format_markdown(selected)

    # 4. 推送到微信
    log("📤 推送到微信...")
    push_wechat(config, content)

    log("🎉 完成！")


if __name__ == "__main__":
    try:
        from bs4 import BeautifulSoup  # noqa
    except ImportError:
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)
    main()
