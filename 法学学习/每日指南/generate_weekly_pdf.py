#!/usr/bin/env python3
"""生成排版精美的周复习总结 PDF —— 从 Markdown 到 A4 打印版

   用法:
     python generate_weekly_pdf.py minfa    # 民法
     python generate_weekly_pdf.py xingfa   # 刑法
"""

import sys, re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ══════════════════════════════════════════════════════════════
#  字体
# ══════════════════════════════════════════════════════════════
FONT_DIR = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("FangSong", f"{FONT_DIR}/simfang.ttf"))   # 仿宋·正文
pdfmetrics.registerFont(TTFont("HeiTi",    f"{FONT_DIR}/simhei.ttf"))    # 黑体·标题
pdfmetrics.registerFont(TTFont("KaiTi",    f"{FONT_DIR}/simkai.ttf"))    # 楷体·引用

# ══════════════════════════════════════════════════════════════
#  配色
# ══════════════════════════════════════════════════════════════
C_PRIMARY    = HexColor("#1a365d")   # 章标题色（深蓝）
C_SECONDARY  = HexColor("#2b6cb0")   # 节标题色（蓝）
C_ACCENT     = HexColor("#9b2c2c")   # 强调色（暗红）
C_BODY       = HexColor("#2d3748")   # 正文色
C_MUTED      = HexColor("#718096")   # 辅助文字
C_BORDER     = HexColor("#e2e8f0")   # 边框
C_TABLE_HDR  = HexColor("#2c5282")   # 表头
C_TABLE_ROW1 = HexColor("#f7fafc")   # 表格奇数行
C_TABLE_ROW2 = HexColor("#ffffff")   # 表格偶数行
C_CALLOUT_BG = HexColor("#fffff0")   # 提示框底

PAGE_W, PAGE_H = A4  # 210 × 297 mm
MARGIN = 2.0 * cm    # 页边距

# ══════════════════════════════════════════════════════════════
#  样式
# ══════════════════════════════════════════════════════════════
S = {}

# ── 封面 ──
S['cover_title'] = ParagraphStyle('cover_title',
    fontName='HeiTi', fontSize=26, leading=38,
    textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=6*mm)
S['cover_sub'] = ParagraphStyle('cover_sub',
    fontName='FangSong', fontSize=11, leading=18,
    textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=4*mm)
S['cover_box_title'] = ParagraphStyle('cover_box_title',
    fontName='HeiTi', fontSize=12, leading=18,
    textColor=C_PRIMARY, alignment=TA_CENTER)
S['cover_box_text'] = ParagraphStyle('cover_box_text',
    fontName='FangSong', fontSize=10, leading=17,
    textColor=C_BODY, alignment=TA_CENTER)
S['cover_footer'] = ParagraphStyle('cover_footer',
    fontName='FangSong', fontSize=9, leading=14,
    textColor=C_MUTED, alignment=TA_CENTER)

# ── 目录 ──
S['toc_title'] = ParagraphStyle('toc_title',
    fontName='HeiTi', fontSize=20, leading=30,
    textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=6*mm)
S['toc_chapter'] = ParagraphStyle('toc_chapter',
    fontName='HeiTi', fontSize=12, leading=22,
    textColor=C_PRIMARY, leftIndent=0*mm, spaceBefore=3*mm)
S['toc_section'] = ParagraphStyle('toc_section',
    fontName='FangSong', fontSize=10.5, leading=19,
    textColor=C_BODY, leftIndent=12*mm)
S['toc_sub'] = ParagraphStyle('toc_sub',
    fontName='FangSong', fontSize=9.5, leading=17,
    textColor=C_MUTED, leftIndent=23*mm)
S['toc_sub2'] = ParagraphStyle('toc_sub2',
    fontName='FangSong', fontSize=9, leading=15,
    textColor=C_MUTED, leftIndent=33*mm)

# ── 正文标题 ──
S['chapter'] = ParagraphStyle('ch',
    fontName='HeiTi', fontSize=19, leading=28,
    textColor=C_PRIMARY, spaceBefore=10*mm, spaceAfter=5*mm)
S['h1'] = ParagraphStyle('h1',
    fontName='HeiTi', fontSize=14, leading=22,
    textColor=C_SECONDARY, spaceBefore=6*mm, spaceAfter=3*mm)
S['h2'] = ParagraphStyle('h2',
    fontName='KaiTi', fontSize=12.5, leading=19,
    textColor=C_SECONDARY, spaceBefore=4*mm, spaceAfter=2*mm)
S['h3'] = ParagraphStyle('h3',
    fontName='HeiTi', fontSize=11, leading=17,
    textColor=C_BODY, spaceBefore=3*mm, spaceAfter=1.5*mm)

# ── 正文 ──
S['body'] = ParagraphStyle('body',
    fontName='FangSong', fontSize=11, leading=22,
    textColor=C_BODY, alignment=TA_JUSTIFY,
    spaceBefore=0.5*mm, spaceAfter=2*mm,
    firstLineIndent=22)
S['body_ni'] = ParagraphStyle('body_ni',
    fontName='FangSong', fontSize=11, leading=22,
    textColor=C_BODY, alignment=TA_JUSTIFY,
    spaceBefore=0.3*mm, spaceAfter=0.3*mm,
    leftIndent=8*mm)
# 编号段落（第一，/第二，/一是/二是 等）
S['enum1'] = ParagraphStyle('enum1',
    fontName='FangSong', fontSize=11, leading=22,
    textColor=C_BODY, alignment=TA_JUSTIFY,
    spaceBefore=2*mm, spaceAfter=1*mm,
    leftIndent=4*mm, firstLineIndent=0)
# 次级编号段落（1./2./①等）
S['enum2'] = ParagraphStyle('enum2',
    fontName='FangSong', fontSize=10.5, leading=21,
    textColor=C_BODY, alignment=TA_JUSTIFY,
    spaceBefore=0.8*mm, spaceAfter=0.8*mm,
    leftIndent=12*mm, firstLineIndent=0)

# ── 引用 ──
S['quote'] = ParagraphStyle('quote',
    fontName='KaiTi', fontSize=10.5, leading=20,
    textColor=HexColor("#5b4636"),
    leftIndent=10*mm, rightIndent=6*mm,
    spaceBefore=2*mm, spaceAfter=3*mm)

# ── 表格 ──
S['th'] = ParagraphStyle('th',
    fontName='HeiTi', fontSize=9, leading=14,
    textColor=white, alignment=TA_CENTER)
S['tc'] = ParagraphStyle('tc',
    fontName='FangSong', fontSize=9, leading=15,
    textColor=C_BODY)


# ══════════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════════
def ch(text):    return Paragraph(text, S['chapter'])
def h1(text):    return Paragraph(text, S['h1'])
def h2(text):    return Paragraph(text, S['h2'])
def h3(text):    return Paragraph(text, S['h3'])
def body(text):  return Paragraph(text, S['body'])
def bni(text):   return Paragraph(text, S['body_ni'])
def enum1(text): return Paragraph(text, S['enum1'])
def enum2(text): return Paragraph(text, S['enum2'])
def hr(w="40%"):
    return HRFlowable(width=w, thickness=0.5, color=C_BORDER,
                       spaceBefore=2*mm, spaceAfter=2*mm, hAlign='LEFT')

def make_table(headers, rows, col_widths=None):
    data = [[Paragraph(h, S['th']) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), S['tc']) for c in row])
    avail = PAGE_W - 2*MARGIN
    if col_widths is None:
        col_widths = [avail / len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), C_TABLE_HDR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    for i in range(1, len(data)):
        bg = C_TABLE_ROW1 if i % 2 == 1 else C_TABLE_ROW2
        cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    t.setStyle(TableStyle(cmds))
    return t


# ══════════════════════════════════════════════════════════════
#  封面 & 目录
# ══════════════════════════════════════════════════════════════
def build_cover(config):
    story = []
    story.append(Spacer(1, 3.5*cm))
    story.append(Paragraph(config['icon'], S['cover_title']))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(config['title'], S['cover_title']))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(config['subtitle'], S['cover_sub']))
    story.append(Spacer(1, 1.5*cm))

    # 章节概览
    ch_lines = []
    for chap, desc in config['chapters']:
        ch_lines.append(f'<b>{chap}</b>&nbsp;&nbsp;&nbsp;{desc}')
    ch_text = '<br/>'.join(ch_lines)

    box_content = Paragraph(
        f'<font color="#2b6cb0"><b>本周覆盖章节</b></font>'
        f'<br/><br/>'
        f'{ch_text}',
        S['cover_box_text']
    )
    box = Table([[box_content]], colWidths=[PAGE_W - 2*MARGIN - 32])
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#ebf4ff")),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEBEFORE', (0, 0), (0, 0), 4, HexColor("#2b6cb0")),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(box)
    story.append(Spacer(1, 2.5*cm))
    story.append(Paragraph('2026年6月1日 — 6月6日 · 第一周复习总结 · 100%基于课本原文', S['cover_footer']))
    story.append(PageBreak())
    return story


def build_toc(toc_entries):
    story = []
    story.append(Spacer(1, 1.5*cm))
    story.append(Paragraph('目&nbsp;&nbsp;录', S['toc_title']))
    story.append(hr("30%"))
    story.append(Spacer(1, 6*mm))

    for level, text in toc_entries:
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        if level == 'chapter':
            story.append(Paragraph(text, S['toc_chapter']))
        elif level == 'h1':
            story.append(Paragraph(text, S['toc_section']))
        elif level == 'h2':
            story.append(Paragraph(text, S['toc_sub']))
        elif level == 'h3':
            story.append(Paragraph(text, S['toc_sub2']))

    story.append(PageBreak())
    return story


def extract_toc(md_text):
    toc = []
    for line in md_text.split('\n'):
        s = line.strip()
        if s.startswith('# ') and not s.startswith('## '):
            toc.append(('chapter', s[2:]))
        elif s.startswith('## ') and not s.startswith('### '):
            toc.append(('h1', s[3:]))
        elif s.startswith('### ') and not s.startswith('#### '):
            toc.append(('h2', s[3:]))
        elif s.startswith('#### '):
            toc.append(('h3', s[4:]))
    return toc


# ══════════════════════════════════════════════════════════════
#  Markdown → PDF 元素
# ══════════════════════════════════════════════════════════════
def parse_inline(text):
    """内联格式"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = text.replace('⭐', '<font color="#9b2c2c">★</font>')
    text = text.replace('→', ' → ')
    return text


# ── 中式序号正则 ──
_RE_ENUM1 = re.compile(r'^(第[一二三四五六七八九十百]+[，、])')  # 第一，第二，...
_RE_ENUM2 = re.compile(
    r'^((?:[一二三四五六七八九十]+(?:是|、|，|．|\.)\s*)'
    r'|(?:其[一二三四五六七八九十]+[，、])'
    r'|(?:[一两]方面[，、]))')  # 一是/二是/其一，/一方面，
_RE_NUM = re.compile(r'^(\d+[\.\、\)）]\s*)')  # 1. 2. 等


def format_paragraph(text):
    """检测中式序号并返回 (style_key, formatted_text)"""
    s = text.strip()

    m = _RE_ENUM1.match(s)
    if m:
        prefix = m.group(1)
        rest = s[m.end():]
        return ('enum1', f'<b>{prefix}</b>{rest}')

    m = _RE_ENUM2.match(s)
    if m:
        prefix = m.group(1)
        rest = s[m.end():]
        return ('enum2', f'<b>{prefix}</b>{rest}')

    m = _RE_NUM.match(s)
    if m:
        prefix = m.group(1)
        rest = s[m.end():]
        return ('enum2', f'<b>{prefix}</b>{rest}')

    return ('body', s)


def parse_markdown_to_story(md_text):
    story = []
    lines = md_text.split('\n')
    i = 0
    first_chapter = True

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 跳过 frontmatter 标题行
        if stripped.startswith('# ') and not stripped.startswith('## '):
            if '总结' in stripped or '知识点' in stripped:
                i += 1
                continue
            # 章标题 —— 新起一页
            if not first_chapter:
                story.append(PageBreak())
            first_chapter = False
            text = parse_inline(stripped[2:])
            story.append(ch(text))
            story.append(HRFlowable(width="35%", thickness=1.5, color=C_SECONDARY,
                                     spaceBefore=0, spaceAfter=3*mm, hAlign='LEFT'))
            i += 1
            continue

        if stripped.startswith('---'):
            story.append(hr())
            i += 1
            continue

        if stripped.startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                quote_lines.append(parse_inline(lines[i].strip()[2:]))
                i += 1
            story.append(Paragraph('<br/>'.join(quote_lines), S['quote']))
            continue

        if stripped.startswith('## ') and not stripped.startswith('### '):
            story.append(h1(parse_inline(stripped[3:])))
            i += 1
            continue

        if stripped.startswith('### ') and not stripped.startswith('#### '):
            story.append(h2(parse_inline(stripped[3:])))
            i += 1
            continue

        if stripped.startswith('#### '):
            story.append(h3(parse_inline(stripped[4:])))
            i += 1
            continue

        # 表格
        if '|' in stripped and stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i].strip():
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) >= 2:
                headers = [parse_inline(c.strip()) for c in table_lines[0].split('|') if c.strip()]
                rows = []
                for tl in table_lines[2:]:
                    cells = [parse_inline(c.strip()) for c in tl.split('|') if c.strip()]
                    if cells:
                        rows.append(cells)
                if headers and rows:
                    avail = PAGE_W - 2*MARGIN
                    cw = [avail / len(headers)] * len(headers)
                    story.append(make_table(headers, rows, cw))
                    story.append(Spacer(1, 3*mm))
            continue

        # 无序列表
        if stripped.startswith('- ') or stripped.startswith('* '):
            bullet_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or
                                       lines[i].strip().startswith('* ')):
                bullet_items.append(parse_inline(lines[i].strip()[2:]))
                i += 1
            for item in bullet_items:
                story.append(bni(f'· {item}'))
            continue

        # 有序列表
        if re.match(r'^\d+\.\s', stripped):
            num_items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                num_items.append(parse_inline(item_text))
                i += 1
            for j, item in enumerate(num_items, 1):
                story.append(bni(f'{j}. {item}'))
            continue

        # 普通段落 —— 智能序号检测
        style_key, formatted = format_paragraph(stripped)
        formatted = parse_inline(formatted)
        if style_key == 'enum1':
            story.append(enum1(formatted))
        elif style_key == 'enum2':
            story.append(enum2(formatted))
        else:
            story.append(body(formatted))
        i += 1

    return story


# ══════════════════════════════════════════════════════════════
#  页眉页脚
# ══════════════════════════════════════════════════════════════
def on_page(canvas, doc):
    canvas.saveState()
    # 页眉线
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 1.6*cm, PAGE_W - MARGIN, PAGE_H - 1.6*cm)
    # 页眉文字
    canvas.setFillColor(C_MUTED)
    canvas.setFont('FangSong', 7.5)
    canvas.drawString(MARGIN, PAGE_H - 1.45*cm, getattr(doc, 'short_title', ''))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.45*cm, getattr(doc, 'full_title', ''))
    # 页脚
    canvas.setStrokeColor(C_BORDER)
    canvas.line(MARGIN, 1.4*cm, PAGE_W - MARGIN, 1.4*cm)
    canvas.setFillColor(C_MUTED)
    canvas.setFont('FangSong', 8)
    canvas.drawRightString(PAGE_W - MARGIN, 1.05*cm, f'- {canvas.getPageNumber()} -')
    canvas.restoreState()


# ══════════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════════
def build_weekly_pdf(input_md, output_pdf, config):
    with open(input_md, 'r', encoding='utf-8') as f:
        md_content = f.read()

    toc_entries = extract_toc(md_content)

    doc = SimpleDocTemplate(
        output_pdf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2*cm, bottomMargin=2*cm,
        title=config['title'], author='法学考研复习系统'
    )
    # 附加信息给页眉使用
    doc.short_title = config['short_title']
    doc.full_title = config['title']

    story = []
    story.extend(build_cover(config))
    story.extend(build_toc(toc_entries))
    story.extend(parse_markdown_to_story(md_content))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f'PDF 已生成: {output_pdf}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('subject', choices=['minfa', 'xingfa'])
    args = parser.parse_args()

    if args.subject == 'minfa':
        config = {
            'title': '民法总论 · 第一周知识点总结',
            'short_title': '民法总论 第一周总结',
            'subtitle': '王利明《民法总则（第二版）》| 第1-3章 + 第5章 + 第11章',
            'icon': '🏛️',
            'chapters': [
                ('第一章 民法概述',    '概念 / 调整对象 / 性质 / 民法典体系 / 渊源'),
                ('第二章 民法基本原则', '八大原则：意思自治 / 公平 / 诚信 / 公序良俗等'),
                ('第三章 民事法律关系', '三要素 / 法律事实（事件 vs 行为）'),
                ('第十一章 民事权利',   '概述 / 基本分类 / 主要类型（人身权 / 物权 / 债权）'),
                ('第五章 自然人',       '权利能力 / 行为能力三档 / 监护 / 宣告失踪与死亡'),
            ]
        }
    else:
        config = {
            'title': '刑法总论 · 第一周知识点总结',
            'short_title': '刑法总论 第一周总结',
            'subtitle': '马工程《刑法学（第二版）》上册 | 第1-6章',
            'icon': '⚖️',
            'chapters': [
                ('第一章 刑法概说',          '概念 / 性质 / 任务 / 体系 / 解释'),
                ('第二章 刑法基本原则',       '罪刑法定 / 适用平等 / 罪责刑相适应'),
                ('第三章 刑法效力范围',       '空间效力 + 时间效力'),
                ('第四章 犯罪概念与犯罪构成', '犯罪三特征 / 犯罪构成四要件体系'),
                ('第五章 犯罪客体',          '概念 / 分类 / 与犯罪对象的区别'),
                ('第六章 犯罪客观方面',       '危害行为 / 危害结果 / 刑法上的因果关系'),
            ]
        }

    subject_name = '民法总论' if args.subject == 'minfa' else '刑法总论'
    input_file = f'_weekly_review/{subject_name}_第一周总结.md'
    output_file = f'_weekly_review/{subject_name}_第一周总结.pdf'
    build_weekly_pdf(input_file, output_file, config)
