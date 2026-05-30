#!/usr/bin/env python3
"""
每日新闻简报 — 自动抓取国内外要闻，生成摘要，发送到 QQ 邮箱。
用法: python daily_news.py
适合配合 Windows 任务计划程序每日定时运行。
"""

import json
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple
from html import escape

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
        "max_items": int(os.environ.get("MAX_ITEMS", "7")),
        "to_email": os.environ.get("TO_EMAIL", ""),
        "smtp": {
            "server": os.environ.get("SMTP_SERVER", "smtp-mail.outlook.com"),
            "port": int(os.environ.get("SMTP_PORT", "587")),
            "sender_email": os.environ.get("SENDER_EMAIL", ""),
            "auth_code": os.environ.get("AUTH_CODE", ""),
        },
    }


# ============================================================
# 新闻源定义
# ============================================================

# RSS 源（较稳定，优先使用）
RSS_SOURCES: List[dict] = [
    # --- 国内 ---
    {
        "name": "新华网-时政",
        "url": "http://www.xinhuanet.com/politics/news_politics.xml",
        "category": "国内",
    },
    {
        "name": "人民网-时政",
        "url": "http://www.people.com.cn/rss/politics.xml",
        "category": "国内",
    },
    {
        "name": "环球网",
        "url": "https://www.huanqiu.com/rss/news.xml",
        "category": "国内",
    },
    # --- 国际 ---
    {
        "name": "BBC 中文",
        "url": "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
        "category": "国际",
    },
    {
        "name": "德国之声中文",
        "url": "https://rss.dw.com/rss/rss-chi-all",
        "category": "国际",
    },
    {
        "name": "FT 中文网",
        "url": "https://www.ftchinese.com/rss/feed",
        "category": "国际",
    },
]

# 网页抓取源（RSS 不可用时的备选）
WEB_SOURCES: List[dict] = [
    {
        "name": "澎湃新闻-要闻",
        "url": "https://www.thepaper.cn/",
        "category": "国内",
    },
    {
        "name": "新浪新闻-要闻",
        "url": "https://news.sina.com.cn/",
        "category": "国内",
    },
    {
        "name": "参考消息",
        "url": "https://www.cankaoxiaoxi.com/",
        "category": "国际",
    },
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
            # RSS 解析失败且没有条目
            return items

        for entry in feed.entries[:15]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            # 清理 HTML 标签
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            # 截断过长摘要
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
        log(f"  ⚠️ RSS 抓取失败 [{source['name']}]: {e}")

    return items


def fetch_web(source: dict) -> List[dict]:
    """从网页抓取新闻标题（简单版，抓 <a> 标签中的标题文本）"""
    items = []
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(source["url"], headers=headers, timeout=15)
        resp.encoding = resp.apparent_encoding or "utf-8"

        # 找页面中可能是新闻标题的链接
        # 通常新闻标题在 <a> 标签中，href 包含日期或 news 关键词
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        seen_titles = set()
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a["href"]

            # 过滤：标题太短或太长都不像新闻标题
            if len(title) < 10 or len(title) > 100:
                continue
            if title in seen_titles:
                continue

            # 补全相对链接
            if href.startswith("/"):
                href = requests.compat.urljoin(source["url"], href)

            seen_titles.add(title)
            items.append({
                "title": title,
                "link": href,
                "summary": "",
                "source": source["name"],
                "category": source["category"],
            })

            if len(items) >= 15:
                break

    except Exception as e:
        log(f"  ⚠️ 网页抓取失败 [{source['name']}]: {e}")

    return items


def fetch_all_news(max_per_source: int = 10) -> List[dict]:
    """从所有源抓取新闻"""
    all_items: List[dict] = []
    seen_titles: set = set()

    # 先试 RSS
    for source in RSS_SOURCES:
        log(f"📡 抓取 RSS: {source['name']}...")
        items = fetch_rss(source)
        log(f"   获取 {len(items)} 条")
        for item in items:
            # 去重（按标题相似度）
            key = item["title"][:30]
            if key not in seen_titles:
                seen_titles.add(key)
                all_items.append(item)
        if len([i for i in all_items if i["category"] == source["category"]]) >= max_per_source * 2:
            continue  # 该分类已经够了

    # 如果某个分类新闻太少，补抓网页
    domestic_count = len([i for i in all_items if i["category"] == "国内"])
    intl_count = len([i for i in all_items if i["category"] == "国际"])

    if domestic_count < 5 or intl_count < 5:
        for source in WEB_SOURCES:
            if (source["category"] == "国内" and domestic_count >= 10) or \
               (source["category"] == "国际" and intl_count >= 10):
                continue
            log(f"🌐 抓取网页: {source['name']}...")
            items = fetch_web(source)
            log(f"   获取 {len(items)} 条")
            for item in items:
                key = item["title"][:30]
                if key not in seen_titles:
                    seen_titles.add(key)
                    all_items.append(item)
                    if item["category"] == "国内":
                        domestic_count += 1
                    else:
                        intl_count += 1

    return all_items


# ============================================================
# 新闻筛选
# ============================================================

# 高优先级关键词 — 标题包含这些词优先入选
HIGH_PRIORITY_KEYWORDS = {
    "国内": [
        "习近平", "国务院", "人大", "法律", "法治", "司法",
        "经济", "GDP", "房地产", "股市", "就业",
        "疫情", "卫生", "教育", "高考", "科技",
        "台湾", "香港", "南海", "军事",
        "最高人民法院", "最高人民检察院", "民法典", "刑法",
    ],
    "国际": [
        "联合国", "美国", "欧盟", "俄罗斯", "日本", "韩国",
        "战争", "冲突", "制裁", "贸易",
        "气候", "AI", "人工智能", "太空",
        "选举", "峰会", "协议",
    ],
}


def score_news(item: dict) -> int:
    """给新闻打分，分数越高越重要"""
    score = 0
    title = item["title"]
    category = item["category"]

    # 高优先级关键词加分
    keywords = HIGH_PRIORITY_KEYWORDS.get(category, [])
    for kw in keywords:
        if kw in title:
            score += 5

    # 标题长度适中（15-50字）加分
    title_len = len(title)
    if 15 <= title_len <= 50:
        score += 3

    # 有摘要加分
    if item.get("summary"):
        score += 2

    return score


def select_top_news(items: List[dict], total: int = 7) -> List[dict]:
    """
    筛选最重要的 N 条新闻，国内国际大致均衡。
    目标比例：国内 4-5 条，国际 3-4 条（总数 7-8）
    """
    domestic = [i for i in items if i["category"] == "国内"]
    international = [i for i in items if i["category"] == "国际"]

    # 按分数排序
    domestic.sort(key=score_news, reverse=True)
    international.sort(key=score_news, reverse=True)

    # 按比例分配
    domestic_n = min(len(domestic), max(3, total - 3))  # 国内至少3条
    intl_n = min(len(international), total - domestic_n)

    # 如果国内不够，国际补
    if domestic_n + intl_n < total:
        extra = total - domestic_n - intl_n
        if len(domestic) > domestic_n:
            domestic_n = min(len(domestic), domestic_n + extra)
        elif len(international) > intl_n:
            intl_n = min(len(international), intl_n + extra)

    selected = domestic[:domestic_n] + international[:intl_n]
    # 二次排序：分数降序
    selected.sort(key=score_news, reverse=True)

    return selected


# ============================================================
# 邮件生成
# ============================================================

def format_email_html(items: List[dict], config: dict) -> str:
    """生成 HTML 邮件内容"""
    today = datetime.now().strftime("%Y年%m月%d日")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][datetime.now().weekday()]
    date_str = f"{today} 星期{weekday}"

    domestic = [i for i in items if i["category"] == "国内"]
    international = [i for i in items if i["category"] == "国际"]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日新闻简报 — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
<tr><td align="center">

<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

<!-- 头部 -->
<tr>
<td style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:28px 32px;text-align:center;">
  <div style="font-size:24px;color:#fff;font-weight:700;letter-spacing:2px;">📰 每日新闻简报</div>
  <div style="font-size:14px;color:#aab;margin-top:6px;">{date_str}</div>
</td>
</tr>

<!-- 正文 -->
<tr>
<td style="padding:24px 32px;">
"""

    # 国内新闻
    if domestic:
        html += """
  <div style="margin-bottom:24px;">
    <div style="font-size:18px;font-weight:700;color:#c41e3a;border-bottom:2px solid #c41e3a;padding-bottom:6px;margin-bottom:12px;">
      🇨🇳 国内要闻
    </div>
"""
        for i, item in enumerate(domestic, 1):
            summary_html = ""
            if item.get("summary"):
                summary_html = f'<div style="font-size:13px;color:#666;margin-top:4px;line-height:1.6;">{escape(item["summary"])}</div>'
            html += f"""
    <div style="margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #f0f0f0;">
      <div style="font-size:15px;line-height:1.6;">
        <span style="color:#c41e3a;font-weight:700;">{i}.</span>
        <a href="{escape(item['link'])}" style="color:#1a1a2e;text-decoration:none;font-weight:500;">{escape(item['title'])}</a>
        <span style="font-size:11px;color:#999;margin-left:6px;">— {escape(item['source'])}</span>
      </div>
      {summary_html}
    </div>"""

        html += "  </div>\n"

    # 国际新闻
    if international:
        html += """
  <div style="margin-bottom:8px;">
    <div style="font-size:18px;font-weight:700;color:#1a56db;border-bottom:2px solid #1a56db;padding-bottom:6px;margin-bottom:12px;">
      🌍 国际要闻
    </div>
"""
        for i, item in enumerate(international, 1):
            summary_html = ""
            if item.get("summary"):
                summary_html = f'<div style="font-size:13px;color:#666;margin-top:4px;line-height:1.6;">{escape(item["summary"])}</div>'
            html += f"""
    <div style="margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid #f0f0f0;">
      <div style="font-size:15px;line-height:1.6;">
        <span style="color:#1a56db;font-weight:700;">{i}.</span>
        <a href="{escape(item['link'])}" style="color:#1a1a2e;text-decoration:none;font-weight:500;">{escape(item['title'])}</a>
        <span style="font-size:11px;color:#999;margin-left:6px;">— {escape(item['source'])}</span>
      </div>
      {summary_html}
    </div>"""

        html += "  </div>\n"

    # 尾部
    html += f"""
</td>
</tr>

<!-- 页脚 -->
<tr>
<td style="background:#fafafa;padding:16px 32px;text-align:center;border-top:1px solid #eee;">
  <div style="font-size:11px;color:#999;line-height:1.8;">
    由每日新闻简报自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}<br>
    <span style="color:#bbb;">本邮件为自动化摘要，不构成新闻推荐。点击标题可查看原文。</span>
  </div>
</td>
</tr>

</table>

</td></tr>
</table>

</body>
</html>"""

    return html


# ============================================================
# 邮件发送（QQ 邮箱 SMTP）
# ============================================================

def send_email(config: dict, html: str):
    """通过 QQ SMTP 发送邮件"""
    smtp_config = config.get("smtp", {})
    smtp_server = smtp_config.get("server", "smtp.qq.com")
    smtp_port = smtp_config.get("port", 465)
    sender_email = smtp_config.get("sender_email", "")
    auth_code = smtp_config.get("auth_code", "")  # QQ 邮箱授权码
    to_email = config.get("to_email", sender_email)

    if not sender_email or not auth_code:
        log("❌ 未配置发件邮箱或授权码，请在 config.json 中填写")
        sys.exit(1)

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"📰 每日新闻简报 — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"新闻简报 <{sender_email}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if smtp_port == 465:
            # SSL 直连
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            # STARTTLS
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()

        server.login(sender_email, auth_code)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()
        log(f"✅ 邮件已发送到 {to_email}")
    except smtplib.SMTPAuthenticationError:
        log("❌ QQ 邮箱认证失败！请检查授权码是否正确（不是 QQ 密码！）")
        log("   获取授权码：QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码")
        sys.exit(1)
    except Exception as e:
        log(f"❌ 邮件发送失败: {e}")
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
    log(f"📊 共抓取 {len(all_news)} 条候选新闻")

    if not all_news:
        log("❌ 未能获取任何新闻，请检查网络连接")
        sys.exit(1)

    # 2. 筛选
    selected = select_top_news(all_news, max_items)
    domestic_n = len([i for i in selected if i["category"] == "国内"])
    intl_n = len([i for i in selected if i["category"] == "国际"])
    log(f"✨ 已筛选 {len(selected)} 条（国内 {domestic_n} + 国际 {intl_n}）")

    for item in selected:
        log(f"  · [{item['category']}] {item['title'][:50]} — {item['source']}")

    # 3. 生成邮件
    log("📧 生成邮件...")
    html = format_email_html(selected, config)

    # 4. 发送
    log("📨 发送邮件...")
    send_email(config, html)

    log("🎉 完成！")


if __name__ == "__main__":
    # 缺少 bs4 时提示安装
    try:
        from bs4 import BeautifulSoup  # noqa: F811
    except ImportError:
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)

    main()
