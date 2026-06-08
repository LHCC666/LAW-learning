# Generate well-formatted weekly review PDF from combined markdown
import sys, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Fonts ──
FONT_DIR = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("SongTi", f"{FONT_DIR}/simfang.ttf"))  # 仿宋（simsunb=ExtB缺常用字）
pdfmetrics.registerFont(TTFont("HeiTi", f"{FONT_DIR}/simhei.ttf"))
pdfmetrics.registerFont(TTFont("KaiTi", f"{FONT_DIR}/simkai.ttf"))
pdfmetrics.registerFont(TTFont("NotoSansSC", f"{FONT_DIR}/simhei.ttf"))

# ── Colors ──
C_PRIMARY   = HexColor("#1a3a5c")
C_SECONDARY = HexColor("#2c5282")
C_ACCENT    = HexColor("#7b241c")
C_BODY      = HexColor("#2d3748")
C_GRAY      = HexColor("#718096")
C_TABLE_HDR = HexColor("#2c5282")
C_TABLE_BG1 = HexColor("#f7fafc")
C_TABLE_BG2 = HexColor("#ffffff")
C_BORDER    = HexColor("#cbd5e0")
C_QUOTE_BG  = HexColor("#fffaeb")

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# ── Styles ──
S = {}
S['title'] = ParagraphStyle('WT', fontName='HeiTi', fontSize=20, leading=30,
                             textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=4*mm)
S['subtitle'] = ParagraphStyle('WS', fontName='NotoSansSC', fontSize=9, leading=14,
                                textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=6*mm)
S['chapter'] = ParagraphStyle('WCH', fontName='HeiTi', fontSize=18, leading=28,
                               textColor=C_PRIMARY, spaceBefore=8*mm, spaceAfter=4*mm)
S['h1'] = ParagraphStyle('WH1', fontName='HeiTi', fontSize=15, leading=22,
                          textColor=C_PRIMARY, spaceBefore=6*mm, spaceAfter=3*mm)
S['h2'] = ParagraphStyle('WH2', fontName='HeiTi', fontSize=13, leading=19,
                          textColor=C_SECONDARY, spaceBefore=4*mm, spaceAfter=2*mm)
S['h3'] = ParagraphStyle('WH3', fontName='KaiTi', fontSize=11.5, leading=17,
                          textColor=C_SECONDARY, spaceBefore=3*mm, spaceAfter=1.5*mm)
S['body'] = ParagraphStyle('WB', fontName='SongTi', fontSize=10, leading=17,
                            textColor=C_BODY, alignment=TA_JUSTIFY, spaceAfter=1.5*mm,
                            firstLineIndent=20)
S['body_ni'] = ParagraphStyle('WBN', fontName='SongTi', fontSize=10, leading=17,
                               textColor=C_BODY, alignment=TA_JUSTIFY, spaceAfter=1.5*mm)
S['quote'] = ParagraphStyle('WQ', fontName='KaiTi', fontSize=9.5, leading=17,
                             textColor=HexColor("#5b4636"), spaceAfter=1.5*mm)
S['th'] = ParagraphStyle('WTH', fontName='HeiTi', fontSize=8.5, leading=13, textColor=white)
S['tc'] = ParagraphStyle('WTC', fontName='SongTi', fontSize=8.5, leading=14, textColor=C_BODY)
S['small'] = ParagraphStyle('WSM', fontName='NotoSansSC', fontSize=8, leading=12, textColor=C_GRAY)
S['cover_title'] = ParagraphStyle('WCT', fontName='HeiTi', fontSize=26, leading=38,
                                   textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=8*mm)

# ── Helpers ──
def chapter(text): return Paragraph(text, S['chapter'])
def h1(text): return Paragraph(text, S['h1'])
def h2(text): return Paragraph(text, S['h2'])
def h3(text): return Paragraph(text, S['h3'])
def body(text): return Paragraph(text, S['body'])
def bni(text): return Paragraph(text, S['body_ni'])
def qt(text): return Paragraph(text, S['quote'])

def make_table(headers, rows, col_widths=None):
    data = [[Paragraph(h, S['th']) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), S['tc']) for c in row])
    if col_widths is None:
        avail = PAGE_W - 2*MARGIN
        col_widths = [avail/len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0,0), (-1,0), C_TABLE_HDR),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]
    for i in range(1, len(data)):
        cmds.append(('BACKGROUND', (0,i), (-1,i), C_TABLE_BG1 if i%2==0 else C_TABLE_BG2))
    t.setStyle(TableStyle(cmds))
    return t

def info_box(content, bg_color=HexColor("#f0fff4")):
    t = Table([[content]], colWidths=[PAGE_W-2*MARGIN-16])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), bg_color),
        ('LEFTPADDING',(0,0),(-1,-1), 12),
        ('RIGHTPADDING',(0,0),(-1,-1), 12),
        ('TOPPADDING',(0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LINEBELOW',(0,0),(-1,-1), 0.5, bg_color),
        ('LINEABOVE',(0,0),(-1,-1), 0.5, bg_color),
    ]))
    return t

def cover_page(title, subtitle, chapters, subject_icon):
    """Generate a nice cover page."""
    story = []
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph(f'{subject_icon} {title}', S['cover_title']))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(subtitle, S['subtitle']))
    story.append(Spacer(1, 1.5*cm))

    # Chapter overview
    ch_items = []
    for ch, desc in chapters:
        ch_items.append(f'<b>{ch}</b> — {desc}')
    ch_text = '<br/>'.join(ch_items)
    story.append(info_box(
        Paragraph(f'<font color="#2c5282"><b>📖 本周覆盖章节</b></font><br/><br/>{ch_text}', S['body_ni']),
        bg_color=HexColor("#ebf4ff")
    ))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        '📅 2026年6月1日 - 6月6日 | 第一周复习 | 基于课本原文整理',
        S['small']
    ))
    story.append(PageBreak())
    return story

def page_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('NotoSansSC', 7)
    canvas.setFillColor(C_GRAY)
    canvas.drawRightString(PAGE_W-MARGIN, PAGE_H-1.2*cm, f'- {canvas.getPageNumber()} -')
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H-1.5*cm, PAGE_W-MARGIN, PAGE_H-1.5*cm)
    canvas.restoreState()

# ── Markdown parser ──
def parse_markdown_to_story(md_text):
    """Parse markdown into a list of reportlab flowables."""
    story = []
    lines = md_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped.startswith('---'):
            story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER,
                                     spaceBefore=2*mm, spaceAfter=2*mm))
            i += 1
            continue

        # Blockquote
        if stripped.startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('> '):
                qt_text = lines[i].strip()[2:]
                qt_text = parse_inline(qt_text)
                quote_lines.append(qt_text)
                i += 1
            story.append(qt('<br/>'.join(quote_lines)))
            continue

        # Chapter title (#)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            text = parse_inline(stripped[2:])
            story.append(chapter(text))
            i += 1
            continue

        # Header level 1 (##)
        if stripped.startswith('## ') and not stripped.startswith('### '):
            text = parse_inline(stripped[3:])
            story.append(h1(text))
            i += 1
            continue

        # Header level 2 (###)
        if stripped.startswith('### '):
            text = parse_inline(stripped[3:])
            story.append(h2(text))
            i += 1
            continue

        # Header level 3 (####)
        if stripped.startswith('#### '):
            text = parse_inline(stripped[4:])
            story.append(h3(text))
            i += 1
            continue

        # Table
        if '|' in stripped and stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i].strip():
                table_lines.append(lines[i].strip())
                i += 1

            # Parse table
            if len(table_lines) >= 2:
                # Header
                headers = [c.strip() for c in table_lines[0].split('|') if c.strip()]
                # Skip separator line (|---|---|)
                rows = []
                for tl in table_lines[2:] if len(table_lines) > 2 else []:
                    cells = [c.strip() for c in tl.split('|') if c.strip()]
                    # Parse inline formatting in cells
                    cells = [parse_inline(c) for c in cells]
                    if cells:
                        rows.append(cells)

                if headers and rows:
                    # Parse inline formatting in headers
                    headers = [parse_inline(h) for h in headers]
                    avail = PAGE_W - 2*MARGIN
                    cw = [avail/len(headers)] * len(headers)
                    story.append(make_table(headers, rows, cw))
                    story.append(Spacer(1, 2*mm))
                elif headers:
                    # Table with only header (unlikely)
                    pass
            continue

        # Unordered list
        if stripped.startswith('- ') or stripped.startswith('* '):
            bullet_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                item_text = lines[i].strip()[2:]
                item_text = parse_inline(item_text)
                bullet_items.append(item_text)
                i += 1
            for item in bullet_items:
                story.append(bni(f'· {item}'))  # middle dot 替代 bullet
            continue

        # Ordered list
        if re.match(r'^\d+\.\s', stripped):
            num_items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                item_text = parse_inline(item_text)
                num_items.append(item_text)
                i += 1
            for j, item in enumerate(num_items, 1):
                story.append(bni(f'{j}. {item}'))
            continue

        # Regular paragraph
        para_text = parse_inline(stripped)
        story.append(body(para_text))
        i += 1

    return story

def parse_inline(text):
    """Parse inline markdown formatting."""
    # Bold: **text** -> <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* -> <i>text</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Inline code: `text` -> <font face="KaiTi">text</font>
    text = re.sub(r'`([^`]+)`', r'<font face="KaiTi">\1</font>', text)
    # Star (use black star ★ instead of emoji ⭐, not in CJK fonts)
    text = text.replace('⭐', '<font color="#c0392b">★</font>')
    # Arrow
    text = text.replace('→', ' → ')
    return text

# ── Main ──
def build_weekly_pdf(input_md, output_pdf, config):
    """Build a weekly review PDF from combined markdown."""
    with open(input_md, 'r', encoding='utf-8') as f:
        md_content = f.read()

    story = []

    # Cover page
    story.extend(cover_page(config['title'], config['subtitle'], config['chapters'], config['icon']))

    # Parse body
    story.extend(parse_markdown_to_story(md_content))

    # Build
    doc = SimpleDocTemplate(
        output_pdf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2*cm, bottomMargin=1.5*cm,
        title=config['title'], author='法学考研复习系统'
    )
    doc.build(story, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    print(f'PDF generated: {output_pdf}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('subject', choices=['minfa','xingfa'])
    args = parser.parse_args()

    if args.subject == 'minfa':
        config = {
            'title': '民法总论 · 第一周知识点总结',
            'subtitle': '王利明《民法总则（第二版）》| 第1-3章 + 第5章 + 第11章',
            'icon': '🏛️',
            'chapters': [
                ('第1章 民法概述', '概念/调整对象/性质/民法典体系/渊源'),
                ('第2章 民法基本原则', '八大原则：意思自治/公平/诚信/公序良俗等'),
                ('第3章 民事法律关系', '三要素/法律事实（事件vs行为）'),
                ('第11章 民事权利', '概述/基本分类/主要类型（人身权/物权/债权）'),
                ('第5章 自然人', '权利能力/行为能力三档/监护/宣告失踪与死亡/两户/住所'),
            ]
        }
    else:
        config = {
            'title': '刑法总论 · 第一周知识点总结',
            'subtitle': '马工程《刑法学（第二版）》上册 | 第1-6章',
            'icon': '⚖️',
            'chapters': [
                ('第1章 刑法概说', '概念/性质/任务/体系/解释'),
                ('第2章 刑法基本原则', '罪刑法定/适用平等/罪责刑相适应'),
                ('第3章 刑法效力范围', '空间效力（属地/属人/保护/普遍管辖）+时间效力'),
                ('第4章 犯罪概念与构成', '犯罪三特征/犯罪构成四要件体系'),
                ('第5章 犯罪客体', '概念/分类/与犯罪对象的区别'),
                ('第6章 犯罪客观方面', '危害行为/危害结果/刑法上的因果关系'),
            ]
        }

    subject_name = '民法总论' if args.subject == 'minfa' else '刑法总论'
    input_file = f'_weekly_review/{subject_name}_第一周总结.md'
    output_file = f'_weekly_review/{subject_name}_第一周总结.pdf'
    build_weekly_pdf(input_file, output_file, config)
