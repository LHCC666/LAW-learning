#!/usr/bin/env python3
"""
将每日复习指南 Markdown 转换为排版精美的 PDF
用法：python generate_pdf.py 每日指南/2026-06-08.md
"""

import sys
import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 注册中文字体（.ttf格式嵌入，安卓不改）─────────────────
FONT_DIR = "C:/Windows/Fonts"

pdfmetrics.registerFont(TTFont("SongTi", f"{FONT_DIR}/simsunb.ttf"))     # 正文宋体
pdfmetrics.registerFont(TTFont("HeiTi", f"{FONT_DIR}/simhei.ttf"))       # 标题黑体
pdfmetrics.registerFont(TTFont("KaiTi", f"{FONT_DIR}/simkai.ttf"))       # 引用楷体
pdfmetrics.registerFont(TTFont("NotoSansSC", f"{FONT_DIR}/simhei.ttf"))  # 辅助用黑体

# ── 颜色方案 ─────────────────────────────────────────────────
C_PRIMARY    = HexColor("#1a3a5c")   # 深蓝 — 主标题
C_SECONDARY  = HexColor("#2c5282")   # 中蓝 — 二级标题
C_ACCENT     = HexColor("#7b241c")   # 深红 — 重要标记
C_BODY       = HexColor("#2d3748")   # 正文
C_LIGHT_BG   = HexColor("#f7fafc")   # 浅灰蓝背景
C_QUOTE_BG   = HexColor("#fffdf0")   # 米黄 — 课本引用
C_TIP_BG     = HexColor("#edf2f7")   # 淡蓝 — 记忆口诀
C_TABLE_HDR  = HexColor("#2c5282")   # 表头色
C_TABLE_BG1  = HexColor("#f7fafc")   # 表行交替1
C_TABLE_BG2  = HexColor("#ffffff")   # 表行交替2
C_BORDER     = HexColor("#cbd5e0")   # 表格边框
C_EXAM_BG    = HexColor("#fff5f5")   # 浅红 — 产出任务
C_LINK_BG    = HexColor("#f0fff4")   # 浅绿 — 跨科串联
C_GRAY       = HexColor("#718096")   # 灰色辅助文字

# ── 页面设置 ─────────────────────────────────────────────────
PAGE_W, PAGE_H = A4  # 210 x 297 mm
MARGIN = 2.2 * cm

# ── 样式定义 ─────────────────────────────────────────────────
def make_styles():
    ss = {}

    ss['title'] = ParagraphStyle(
        'CTitle', fontName='HeiTi', fontSize=22, leading=32,
        textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=6*mm,
    )
    ss['subtitle'] = ParagraphStyle(
        'CSubtitle', fontName='NotoSansSC', fontSize=10, leading=16,
        textColor=C_GRAY, alignment=TA_CENTER, spaceAfter=8*mm,
    )
    ss['h1'] = ParagraphStyle(
        'CH1', fontName='HeiTi', fontSize=15, leading=22,
        textColor=C_PRIMARY, spaceBefore=8*mm, spaceAfter=4*mm,
        borderPadding=(0, 0, 2, 0),
    )
    ss['h2'] = ParagraphStyle(
        'CH2', fontName='HeiTi', fontSize=12, leading=18,
        textColor=C_SECONDARY, spaceBefore=5*mm, spaceAfter=2*mm,
    )
    ss['h3'] = ParagraphStyle(
        'CH3', fontName='KaiTi', fontSize=11, leading=17,
        textColor=C_SECONDARY, spaceBefore=3*mm, spaceAfter=1.5*mm,
    )
    ss['body'] = ParagraphStyle(
        'CBody', fontName='SongTi', fontSize=10, leading=18,
        textColor=C_BODY, alignment=TA_JUSTIFY, spaceAfter=1.5*mm,
        firstLineIndent=2*10,  # 2字符缩进
    )
    ss['body_ni'] = ParagraphStyle(  # no indent
        'CBodyNI', fontName='SongTi', fontSize=10, leading=18,
        textColor=C_BODY, alignment=TA_JUSTIFY, spaceAfter=1.5*mm,
    )
    ss['quote'] = ParagraphStyle(
        'CQuote', fontName='KaiTi', fontSize=10, leading=18,
        textColor=HexColor("#5b4636"), spaceAfter=1.5*mm,
    )
    ss['small'] = ParagraphStyle(
        'CSmall', fontName='NotoSansSC', fontSize=8.5, leading=14,
        textColor=C_GRAY,
    )
    ss['table_header'] = ParagraphStyle(
        'CTH', fontName='HeiTi', fontSize=9, leading=14,
        textColor=white,
    )
    ss['table_cell'] = ParagraphStyle(
        'CTC', fontName='SongTi', fontSize=9, leading=15,
        textColor=C_BODY,
    )
    ss['table_cell_bold'] = ParagraphStyle(
        'CTCB', fontName='HeiTi', fontSize=9, leading=15,
        textColor=C_BODY,
    )
    ss['stat_label'] = ParagraphStyle(
        'CStatLabel', fontName='HeiTi', fontSize=10, leading=20,
        textColor=C_GRAY,
    )
    ss['stat_value'] = ParagraphStyle(
        'CStatValue', fontName='HeiTi', fontSize=18, leading=24,
        textColor=C_PRIMARY,
    )
    return ss

S = make_styles()

# ── 辅助函数 ─────────────────────────────────────────────────

def h1(text):
    """一级标题 + 下划线"""
    return [
        Paragraph(text, S['h1']),
        HRFlowable(width="100%", thickness=1.5, color=C_PRIMARY, spaceAfter=3*mm),
    ]

def h2(text):
    return Paragraph(text, S['h2'])

def h3(text):
    return Paragraph(text, S['h3'])

def body(text):
    return Paragraph(text, S['body'])

def body_ni(text):
    return Paragraph(text, S['body_ni'])

def quote(text):
    """课本原文引用 — 楷体+缩进+米黄底"""
    return Paragraph(
        f'<font color="#b7791f">📖 </font>{text}',
        S['quote']
    )

def spacer(mm_val=3):
    return Spacer(1, mm_val * mm)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceBefore=2*mm, spaceAfter=2*mm)

def bullet(items, indent=1):
    """无序列表"""
    result = []
    prefix = "　" * indent + "• "
    for item in items:
        result.append(Paragraph(f"{prefix}{item}", S['body_ni']))
    return result

def numbered(items, indent=1):
    """有序列表"""
    result = []
    prefix = "　" * indent
    for i, item in enumerate(items, 1):
        result.append(Paragraph(f"{prefix}{i}. {item}", S['body_ni']))
    return result

def make_table(headers, rows, col_widths=None):
    """创建格式化表格"""
    hdr_cells = [Paragraph(h, S['table_header']) for h in headers]
    data = [hdr_cells]

    for row in rows:
        data.append([Paragraph(str(c), S['table_cell']) for c in row])

    if col_widths is None:
        avail = PAGE_W - 2 * MARGIN
        col_widths = [avail / len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), C_TABLE_HDR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'HeiTi'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    # 交替行色
    for i in range(1, len(data)):
        bg = C_TABLE_BG1 if i % 2 == 0 else C_TABLE_BG2
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

    t.setStyle(TableStyle(style_cmds))
    return t

def info_box(content, bg_color=C_LIGHT_BG, border_color=None):
    """带背景色的信息框"""
    if border_color is None:
        border_color = bg_color
    t = Table([[content]], colWidths=[PAGE_W - 2 * MARGIN - 16])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, border_color),
        ('LINEABOVE', (0, 0), (-1, -1), 0.5, border_color),
        ('LINEBEFORE', (0, 0), (-1, -1), 0.5, border_color),
        ('LINEAFTER', (0, 0), (-1, -1), 0.5, border_color),
    ]))
    return t

def page_header_footer(canvas, doc):
    """页眉页脚"""
    canvas.saveState()
    # 页眉
    canvas.setFont('NotoSansSC', 7)
    canvas.setFillColor(C_GRAY)
    canvas.drawString(MARGIN, PAGE_H - 1.4 * cm,
                      "📅 6/8 周一 复习指南 Day 7 | 法人制度 + 因果关系 + 三段论")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.4 * cm,
                           "法学考研复习 · 2026")
    # 分割线
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 1.6 * cm, PAGE_W - MARGIN, PAGE_H - 1.6 * cm)
    # 页脚
    canvas.setFont('NotoSansSC', 7)
    canvas.drawRightString(PAGE_W - MARGIN, 1.2 * cm, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


# ── 主生成函数 ────────────────────────────────────────────────

def build_pdf(input_md: str, output_pdf: str):
    """从 Markdown 读取内容生成 PDF"""

    # 读取原始内容
    with open(input_md, 'r', encoding='utf-8') as f:
        md_content = f.read()

    story = []

    # ══════════════════════════════════════════════════════════
    # 封面 / 标题区
    # ══════════════════════════════════════════════════════════

    story.append(spacer(15))
    story.append(Paragraph("📅 法学考研复习指南", S['title']))
    story.append(spacer(2))
    story.append(Paragraph(
        "Day 7 · 2026年6月8日 星期一 · 第二周",
        S['subtitle']
    ))

    # 统计卡片
    stat_data = [
        [Paragraph("🏛️ 民法总论", S['stat_label']),
         Paragraph("⚖️ 刑法总论", S['stat_label']),
         Paragraph("🧠 法律逻辑学", S['stat_label'])],
        [Paragraph("50<font size='7'> min</font>", S['stat_value']),
         Paragraph("50<font size='7'> min</font>", S['stat_value']),
         Paragraph("40<font size='7'> min</font>", S['stat_value'])],
        [Paragraph("法人制度", S['small']),
         Paragraph("危害结果+因果关系", S['small']),
         Paragraph("三段论", S['small'])],
    ]
    stat_table = Table(stat_data, colWidths=[(PAGE_W - 2*MARGIN - 2*cm)/3]*3)
    stat_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBEFORE', (0, 0), (0, -1), 1, C_BORDER),
        ('LINEBEFORE', (1, 0), (1, -1), 1, C_BORDER),
        ('LINEBEFORE', (2, 0), (2, -1), 1, C_BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), C_LIGHT_BG),
    ]))
    story.append(spacer(5))
    story.append(stat_table)
    story.append(spacer(8))

    # 本周主题
    story.append(info_box(
        Paragraph(
            '<font color="#2c5282"><b>📌 本周核心：</b></font>'
            '民法法律主体收尾 + 刑法犯罪论深化 + 逻辑演绎推理 ⭐',
            S['body_ni']
        ),
        bg_color=HexColor("#ebf4ff"),
    ))
    story.append(spacer(5))

    # ══════════════════════════════════════════════════════════
    # 第一部分：民法总论
    # ══════════════════════════════════════════════════════════
    story.extend(h1("🏛️ 民法总论 — 第六章 法人的一般原理 + 第七章 营利法人"))

    # 章节概览表
    story.append(h3("📖 今日章节与范围"))
    minfa_chapters = [
        ["第六章 §1", "法人的概念和性质", "概念/特征/性质三学说/分支机构", "★★★"],
        ["第六章 §2", "法人的分类", "公/私、营利/非营利、社团/财团", "★★★"],
        ["第六章 §3", "法人的民事权利能力和行为能力", "特殊性/侵权能力", "★★"],
        ["第六章 §4", "法人的设立与登记", "设立方式五种/设立条件/登记效力", "★★★"],
        ["第六章 §5", "法人的法定代表人", "地位/责任/代表权限制/善意相对人", "★★★"],
        ["第六章 §6", "法人的终止", "解散/清算/注销登记", "★★"],
        ["第七章 §1-3", "营利法人", "概念类型/组织机构/特殊规则", "★★★"],
    ]
    story.append(make_table(
        ["章 节", "内容", "关键词", "考频"],
        minfa_chapters,
        [PAGE_W*0.15, PAGE_W*0.25, PAGE_W*0.40, PAGE_W*0.12]
    ))
    story.append(spacer(4))

    # ── 第一节 法人的概念和性质 ──
    story.append(h2("§1 法人的概念和性质"))

    story.append(body("《民法典》第57条：法人是具有民事权利能力和民事行为能力，依法独立享有民事权利和承担民事义务的组织。"))

    story.append(h3("四项基本特征"))
    features = [
        ["<b>独立的名义</b>", "法人能以自己的名义独立地享有权利、承担义务，并能在法院起诉应诉。法人具有组织上的统一性，从而极大地降低了交易费用。"],
        ["<b>独立的财产</b>", "法人所具有的独立于其投资人以及法人的成员的财产。法人财产与出资人财产分开，在法人内部实行所有权与经营权分离。"],
        ["<b>健全的组织机构</b>", "对内管理法人的事务、对外代表法人从事民事活动的机构的总称。营利法人实行决策、执行、监督机构三权制衡。"],
        ["<b>独立的责任</b>", "《民法典》第60条：法人以其全部财产独立承担民事责任。法人成员承担有限责任是区分法人和非法人组织的重要特征。"],
    ]
    story.append(make_table(
        ["特征", "要点"],
        features,
        [PAGE_W*0.18, PAGE_W*0.74]
    ))
    story.append(spacer(3))

    story.append(h3("法人的性质 — 三学说"))
    nature_data = [
        ["拟制说", "法人是法律拟制的人格，无意思属性", "法人本身无行为能力，须由自然人代理"],
        ['否认说', '法人无独立人格，只是“目的财产”', '实际权利义务归属于管理财产的自然人'],
        ["实在说", "法人是客观存在的主体，有团体意志", "法人机构的行为就是法人自己的行为"],
    ]
    story.append(make_table(
        ["学说", "核心观点", "对行为能力的看法"],
        nature_data,
        [PAGE_W*0.14, PAGE_W*0.36, PAGE_W*0.42]
    ))
    story.append(quote('我国采纳“实在说”，但例外情况下可吸收拟制说的合理之处——法人机构违反法人意志损害法人利益的行为，不应一概由法人承受。'))
    story.append(spacer(2))

    # ── 第二节 法人的分类 ──
    story.append(h2("§2 法人的分类"))

    story.append(h3("分类一：公法人与私法人"))
    story.append(make_table(
        ["", "公法人", "私法人"],
        [["设立依据", "依公法设立", "依私法设立"],
         ["目的", "行使公共行政职能", "一般不履行公共行政职能"],
         ["举例", "机关法人（县、市等）", "公司、企业等"]],
        [PAGE_W*0.16, PAGE_W*0.38, PAGE_W*0.38]
    ))
    story.append(spacer(3))

    story.append(h3("分类二：营利法人与非营利法人"))
    yl_fl = [
        ["概念", "以取得利润并分配给股东等出资人为目的（第76条第1款）", "为公益或其他非营利目的成立，不向出资人分配利润（第87条第1款）"],
        ["设立依据", "特别法（公司法等）", "特别法（慈善法、基金法等）"],
        ["设立原则", "准则主义为主", "许可主义为主"],
        ["<b>核心区别</b>", "利润分配给出资人", "利润归属于法人"],
        ["终止后剩余财产", "分配给成员", "公益法人不得分配，非公益可分配"],
        ["举例", "有限责任公司、股份有限公司", "事业单位、社会团体、基金会"],
    ]
    story.append(make_table(
        ["", "营利法人", "非营利法人"],
        yl_fl,
        [PAGE_W*0.18, PAGE_W*0.37, PAGE_W*0.37]
    ))
    story.append(spacer(3))

    story.append(h3("分类三：社团法人与财团法人"))
    st_ct = [
        ["成立基础", "社员（人的集合）", "财产（捐助行为）"],
        ["目的", "可为营利或公益", "只能为公益"],
        ["设立程序", "符合法定条件即可", "一般需主管机关许可"],
        ["设立人地位", "设立后取得社员资格", "设立后与法人脱离关系"],
        ["举例", "公司、行业协会", "基金会、寺庙"],
    ]
    story.append(make_table(
        ["", "社团法人", "财团法人"],
        st_ct,
        [PAGE_W*0.16, PAGE_W*0.38, PAGE_W*0.38]
    ))
    story.append(body("《民法典》未采纳社团/财团分类，但捐助法人（基金会等）实质上属于财团法人。"))
    story.append(spacer(2))

    # ── 第三节 ──
    story.append(h2("§3 法人的民事权利能力和民事行为能力"))
    story.append(body("《民法典》第59条：权利能力从法人成立时产生，到法人终止时消灭。"))
    story.append(h3("权利能力的特殊性"))
    story.extend(bullet([
        "不享有与公民的人身不可分离的权利（如生命权、健康权），但可以享有名称权、荣誉权、名誉权等人格权",
        "依法受法律、行政法规的限制",
        "受其章程和目的的限制",
    ]))
    story.append(h3("法人 vs 自然人行为能力"))
    story.append(make_table(
        ["", "法人", "自然人"],
        [["时间", "与权利能力同时产生、同时消灭", "受年龄、健康影响"],
         ["范围", "与权利能力一致", "可能小于权利能力"],
         ["意思基础", "区别于单个自然人的团体意思", "个人意思"]],
        [PAGE_W*0.15, PAGE_W*0.40, PAGE_W*0.37]
    ))
    story.append(h3("目的范围对法人能力的限制 — 四种学说"))
    story.append(make_table(
        ["学说", "观点"],
        [["权利能力限制说", "目的范围限制的是权利能力"],
         ["行为能力限制说", "目的范围限制的是行为能力"],
         ["代表权限制说", "目的范围仅划定代表权范围"],
         ["内部责任说", "目的范围仅决定内部责任"]],
        [PAGE_W*0.22, PAGE_W*0.70]
    ))
    story.append(quote("课本立场：机关法人→权利能力限制；营利法人→行为能力限制。营利法人超越经营范围的行为不能简单认定无效。"))
    story.append(spacer(2))

    # ── 第四节 ──
    story.append(h2("§4 法人的设立与登记"))

    story.append(h3("设立方式五种"))
    story.append(make_table(
        ["方式", "内容", "历史阶段"],
        [["自由主义", "具备法人实质即承认", "18-19世纪，现基本放弃"],
         ["特许主义", "专门颁布法律成立特定法人", "—"],
         ["核准主义", "须经行政机关许可", "—"],
         ["<b>准则主义</b>", "符合法定条件即可登记成立", "我国营利法人原则上采此"],
         ["强制主义", "国家强制设立", "—"]],
        [PAGE_W*0.16, PAGE_W*0.48, PAGE_W*0.28]
    ))
    story.append(spacer(2))
    story.append(h3("设立条件（《民法典》第58条第2款）"))
    story.extend(numbered([
        "<b>名称</b>——区别于其他法人的标志，法人对登记注册的名称享有专用权",
        "<b>组织机构</b>——决策机构（股东会）+ 执行机构（董事会）+ 监督机构（监事会）",
        "<b>住所</b>——以其主要办事机构所在地为住所（第63条）",
        "<b>财产或者经费</b>——独立财产是其承担民事责任的物质基础",
    ]))
    story.append(spacer(1))
    story.append(quote("<b>登记效力：</b>登记要件主义——法人经登记成立。《民法典》第65条：实际情况与登记事项不一致的，<b>不得对抗善意相对人</b>。"))
    story.append(spacer(2))

    # ── 第五节 ──
    story.append(h2("§5 法人的法定代表人"))
    story.append(body("《民法典》第61条第1款：依照法律或者法人章程的规定，代表法人从事民事活动的负责人，为法人的法定代表人。"))

    story.append(h3("法定代表人三个特征"))
    story.extend(numbered([
        "由法律或法人章程规定的自然人",
        "有权代表法人从事民事活动（不需要特别授权）",
        "以法人名义从事的活动，由法人承担法律后果（第61条第2款）",
    ]))
    story.append(spacer(1))
    story.append(body("因<b>执行职务</b>造成他人损害的，由法人承担民事责任（第62条第1款）。执行职务的认定标准 → <b>外观说（客观说）</b>。法人承担责任后，可向有过错的法定代表人追偿（第62条第2款）。"))
    story.append(quote("<b>第61条第3款：</b>法人章程或者法人权力机构对法定代表人代表权的限制，<b>不得对抗善意相对人</b>。"))
    story.append(spacer(2))

    # ── 第六节 ──
    story.append(h2("§6 法人的终止"))
    story.append(body("《民法典》第68条第1款：有下列原因之一并依法完成清算、注销登记的，法人终止：（一）法人解散；（二）法人被宣告破产；（三）法律规定的其他原因。"))

    story.append(h3("终止流程"))
    story.append(body_ni(
        '　　<b><font color="#2c5282">解散/破产</font></b>  '
        '<font color="#718096">──────→</font>  '
        '<b><font color="#2c5282">清算</font></b>  '
        '<font color="#718096">──────→</font>  '
        '<b><font color="#2c5282">注销登记</font></b>  '
        '<font color="#718096">──────→</font>  '
        '<b>法人终止</b>'
    ))
    story.append(spacer(2))
    story.append(body("解散事由（第69条）：章程届满或解散事由出现；权力机构决议解散；因合并或分立解散；被吊销/责令关闭/撤销；法律规定的其他情形。"))
    story.append(body("清算期间法人存续，但不得从事与清算无关的活动。清算义务人：董事、理事等执行/决策机构成员。课本立场采<b>同一人格说</b>——清算前后的法人具有同一人格。"))
    story.append(spacer(2))

    # ── 第七章 营利法人 ──
    story.append(h2("第七章 营利法人"))

    story.append(body("《民法典》第76条第1款：营利法人是指以取得利润并分配给股东等出资人为目的成立的法人。"))
    story.append(h3("营利法人的组织机构（三权分立）"))
    story.append(make_table(
        ["机构", "功能", "组成"],
        [["权力机构", "修改章程、选举更换执行/监督机构成员", "股东会/股东大会"],
         ["执行机构", "执行决议、日常管理", "董事会/执行董事"],
         ["监督机构", "监督执行机构活动", "监事会/监事"]],
        [PAGE_W*0.18, PAGE_W*0.40, PAGE_W*0.34]
    ))
    story.append(spacer(2))
    story.append(h3("营利法人的特殊规则"))
    story.extend(numbered([
        "<b>法人人格否认（揭开公司面纱）：</b>不得滥用法人独立地位和有限责任损害债权人利益",
        "<b>关联交易规则：</b>《民法典》第84条——不得利用关联关系损害法人利益，造成损失应赔偿",
        "<b>决议撤销：</b>内容/程序违反法律或章程 → 出资人可申请撤销",
    ]))
    story.append(spacer(2))

    # ── 记忆口诀 ──
    tips_minfa = [
        '<b>法人四特征</b> —— 「名财组责」：独立名义→独立财产→健全组织→独立责任，四个"独"',
        '<b>法人性质三说</b> —— 「拟否实」：拟制→否认→实在，越往后越"真实"',
        "<b>设立五方式</b> —— 「自特核准强」：自由主义→特许主义→核准主义→准则主义→强制主义",
        "<b>营利 vs 非营利</b> —— 「分不分利润」是关键，不在是否营利而在利润是否分配给成员",
        "<b>社团 vs 财团</b> —— 「人合 vs 钱合」：社团靠人、财团靠钱",
        "<b>法定代表人</b> —— 「外观说」来判断执行职务：社会一般人怎么看，法律就怎么认定",
    ]
    story.append(h3("🧠 记忆口诀"))
    for t in tips_minfa:
        story.extend(bullet([t], indent=0))
    story.append(spacer(3))

    # ── 产出任务 ──
    story.append(h3("✏️ 产出任务"))
    tasks_minfa = [
        "闭书画出法人特征四要点 + 默写法人的法条定义（第57条），写完后对照课本核对",
        "画出三分法对比表：营利法人 vs 非营利法人的五点区别",
        "默写因果关系特点六项，写出每项的关键词",
        "案例分析：某公司董事长甲以个人名义购买字画挂在家中，后主张由公司付款。问：公司是否应承担付款义务？写出法律依据。",
    ]
    story.extend(numbered(tasks_minfa))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════
    # 第二部分：刑法总论
    # ══════════════════════════════════════════════════════════
    story.extend(h1("⚖️ 刑法总论 — 第六章 §3 危害结果 + §4 因果关系"))

    xf_chapters = [
        ["第三节", "危害结果", "广义/狭义、四种分类", "★★★"],
        ["第四节", "刑法上的因果关系", "概念/六特点/性质/五种特殊认定", "★★★"],
    ]
    story.append(make_table(
        ["节", "内容", "关键词", "考频"],
        xf_chapters,
        [PAGE_W*0.15, PAGE_W*0.30, PAGE_W*0.35, PAGE_W*0.12]
    ))
    story.append(spacer(4))

    # ── §3 危害结果 ──
    story.append(h2("§3 危害结果"))

    story.append(h3("概念"))
    story.append(quote("<b>广义危害结果：</b>犯罪行为对刑法所保护的社会关系所造成的损害——包括构成要件结果和非构成要件结果、物质性和非物质性、直接结果和间接结果等。"))
    story.append(quote("<b>狭义危害结果（构成要件结果）：</b>由犯罪的实行行为造成的、根据刑法分则的规定对成立犯罪或者犯罪既遂具有决定意义的危害结果——只存在于过失犯罪、间接故意犯罪和结果犯的既遂犯中。"))
    story.append(body("课本立场：危害结果<b>不是一切犯罪构成的必要要件</b>。"))
    story.append(spacer(2))

    story.append(h3("四种分类"))
    # 分类一
    story.append(body_ni("<b>（一）构成要件结果 vs 非构成要件结果</b>"))
    story.append(make_table(
        ["", "构成要件结果（定罪结果）", "非构成要件结果（量刑结果）"],
        [["意义", "对定罪具有决定意义", "对量刑具有评价意义"],
         ["包含", "—", "行为犯结果、预备/未遂/中止犯结果、间接结果、精神损害"]],
        [PAGE_W*0.12, PAGE_W*0.40, PAGE_W*0.40]
    ))
    story.append(spacer(2))

    # 分类二
    story.append(body_ni("<b>（二）物质性危害结果 vs 非物质性危害结果</b>"))
    story.append(make_table(
        ["", "物质性（有形）", "非物质性（无形）"],
        [["特征", "具体、可见、可计量", "抽象、不可直接测量"],
         ["时机", "一般在实行行为实施完毕后才发生", "—"],
         ["举例", "死亡、伤害、财产损害", "名誉受损、人格侮辱、威信受损"]],
        [PAGE_W*0.12, PAGE_W*0.40, PAGE_W*0.40]
    ))
    story.append(spacer(2))

    # 分类三
    story.append(body_ni("<b>（三）直接结果 vs 间接结果</b>"))
    story.append(make_table(
        ["", "直接结果", "间接结果"],
        [["定义", "危害行为本身直接引起", "由直接结果进一步引起"],
         ["与构成要件关系", "构成要件结果只能是直接结果", "只能是量刑情节"]],
        [PAGE_W*0.18, PAGE_W*0.37, PAGE_W*0.37]
    ))
    story.append(spacer(2))

    # 分类四
    story.append(body_ni("<b>（四）基本结果 vs 加重结果</b>"))
    story.append(make_table(
        ["", "基本结果", "加重结果"],
        [["定义", "作为犯罪构成要件的结果", "引起另一种严重危害结果"],
         ["法律效果", "基本构成的要件", "加重构成的要件（结果加重犯）"],
         ["注意", "—", "以刑法明文规定为限，不发生未遂问题"]],
        [PAGE_W*0.18, PAGE_W*0.37, PAGE_W*0.37]
    ))
    story.append(spacer(3))

    # ── §4 因果关系 ⭐ ──
    story.append(h2("§4 刑法上的因果关系 ⭐"))

    story.append(body("刑法上的因果关系，是指人的危害行为合乎规律地引起某种危害结果的内在联系。"))
    story.append(spacer(2))

    story.append(h3("因果关系的六大特点"))
    yg_gx = [
        ["<b>1. 客观性</b>", "不以人的意志为转移的客观存在；不能凭司法人员臆测确定", "客观存在"],
        ["<b>2. 相对性</b>", "必须从普遍联系的链条中抽取危害行为与危害结果这对现象", "抽取一对现象"],
        ["<b>3. 时间顺序性</b>", "原因在先，结果在后，不可颠倒；但在先行为不一定都是原因", "先因后果"],
        ["<b>4. 条件性</b>", "因果关系是具体的、有条件的，不能脱离案件具体条件", "具体条件"],
        ["<b>5. 复杂性</b>", "一因多果（一个行为引起多种结果）、一果多因（多个原因引起一个结果）", "一因多果 / 一果多因"],
        ["<b>6. 必然性和偶然性</b>", "必然因果关系与偶然因果关系是两种表现形式，因果关系本身是必然性和偶然性的统一", "必然+偶然统一"],
    ]
    story.append(make_table(
        ["特点", "核心内容", "关键词"],
        yg_gx,
        [PAGE_W*0.18, PAGE_W*0.56, PAGE_W*0.18]
    ))
    story.append(spacer(3))

    story.append(h3("因果关系的性质"))
    story.extend(numbered([
        "作为原因的行为必须具有引起危害结果发生的<b>现实可能性</b>——因果之间具有质的同一性",
        "作为原因的行为必须<b>合乎规律地</b>引起危害结果的发生——结果必须具有回避可能性",
    ]))
    story.append(spacer(2))

    story.append(h3("五种特殊因果关系认定"))
    special_yg = [
        ["<b>假定的因果关系</b>", "即使没有该行为，其他情况也会产生同样结果", "仍应肯定因果关系的存在"],
        ["<b>重叠的因果关系</b>", "两个以上独立行为单独不能导致结果，合并导致结果", "均肯定因果关系"],
        ["<b>流行病学的因果关系</b>", "公害犯罪（污染环境等），排污行为与污染结果之间", "必要条件 + 病因学旁证法（四条件）"],
        ["<b>不作为犯的因果关系</b>", "不履行作为义务与危害结果的关系", "原因力在于「应阻未阻」"],
        ["<b>中断的因果关系</b>", "因果关系进程中介入其他原因，切断原来因果进程", "综合三因素：可能性+异常性+贡献"],
    ]
    story.append(make_table(
        ["类型", "定义", "认定规则"],
        special_yg,
        [PAGE_W*0.18, PAGE_W*0.34, PAGE_W*0.40]
    ))
    story.append(spacer(2))
    story.append(quote("<b>中断的因果关系三因素：</b>①实行行为导致结果的可能性高低 ②介入因素异常性大小 ③介入因素对结果的贡献大小"))
    story.append(spacer(2))
    story.append(quote("<b>因果关系 ≠ 刑事责任：</b>存在因果关系不等于必然承担刑事责任，还需具备主观罪过。"))
    story.append(spacer(3))

    # 刑法记忆口诀
    story.append(h3("🧠 记忆口诀"))
    tips_xf = [
        "<b>危害结果四分类</b> —— 「构件基物」：构成要件→物质性→直接→基本，每个维度二分法",
        "<b>因果关系六特点</b> —— 「客相时序条复必」：客观性→相对性→时间顺序性→条件性→复杂性→必然偶然性",
        "<b>中断的因果关系</b> —— 「三因素：可能+异常+贡献」",
        "<b>不作为的原因力</b> —— 「应阻未阻」：应该阻止危险发展，却没有阻止",
    ]
    for t in tips_xf:
        story.extend(bullet([t], indent=0))
    story.append(spacer(3))

    # 刑法产出任务
    story.append(h3("✏️ 产出任务"))
    tasks_xf = [
        "默写危害结果的四种分类（含二级分类），每类注明一个举例",
        "默写因果关系六大特点，为每个特点用一句话解释",
        '辨析判断题：甲将乙打成轻伤，乙住院后医生丙用未消毒器械治疗致乙感染死亡。甲的殴打行为与乙的死亡之间是否存在刑法上的因果关系？为什么？（提示：用因果关系"现实可能性"标准分析）',
        '动手写：自编一个"中断的因果关系"小案例，标注三个判断因素',
    ]
    story.extend(numbered(tasks_xf))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════
    # 第三部分：法律逻辑学
    # ══════════════════════════════════════════════════════════
    story.extend(h1("🧠 法律逻辑学 — 第八章 §1 三段论"))

    lj_chapters = [
        ["第一节", "三段论", "特征/组成/规则/格和式/省略式", "★★★"],
    ]
    story.append(make_table(
        ["节", "内容", "关键词", "考频"],
        lj_chapters,
        [PAGE_W*0.15, PAGE_W*0.30, PAGE_W*0.35, PAGE_W*0.12]
    ))
    story.append(spacer(4))

    story.append(h2("§1 三段论的特征和组成"))
    story.append(body("三段论：由两个包含共同词项的性质命题推出一个新的性质命题的演绎推理。"))
    story.append(spacer(2))

    story.append(h3("三段论结构"))
    # 三段论示意图
    sld_structure = [
        ["大前提", "所有 M 是 P", "（包含大项P的命题）"],
        ["小前提", "所有 S 是 M", "（包含小项S的命题）"],
        ["<b>结 论</b>", "<b>所有 S 是 P</b>", "（推出S与P的关系）"],
    ]
    story.append(make_table(
        ["", "命题", "说明"],
        sld_structure,
        [PAGE_W*0.12, PAGE_W*0.38, PAGE_W*0.42]
    ))
    story.append(spacer(2))

    story.append(h3("三个词项"))
    sld_terms = [
        ["<b>大项 P</b>", "大前提的谓项 + 结论的谓项", "结论的谓项"],
        ["<b>中项 M</b>", "大前提和小前提中都出现", "<b>连接大小前提的关键 ⭐</b>"],
        ["<b>小项 S</b>", "小前提的主项 + 结论的主项", "结论的主项"],
    ]
    story.append(make_table(
        ["词项", "位置", "说明"],
        sld_terms,
        [PAGE_W*0.15, PAGE_W*0.42, PAGE_W*0.35]
    ))
    story.append(spacer(3))

    # ── 三段论六条规则 ──
    story.append(h3("三段论的六条关键规则 ⭐⭐"))
    rules = [
        ['<b>规则一</b>', '中项必须至少在一个前提中周延', '“有些M是P，有些S是M” → 中项M两次不周延 ❌'],
        ['<b>规则二</b>', '前提中不周延的词项在结论中不得周延', '前提中“S是P的种”→结论不能说“所有S是P”'],
        ["<b>规则三</b>", "两个否定前提不能得出结论", "M不是P，S不是M → 推不出S和P的关系"],
        ["<b>规则四</b>", "前提有一否定，结论必否定", "M是P，S不是M → 结论应为否定"],
        ['<b>规则五</b>', '两个特称前提不能得出结论', '“有些M是P，有些S是M” → 推不出'],
        ['<b>规则六</b>', '前提有一特称，结论必特称', '“所有M是P，有些S是M” → 结论：“有些S是P”'],
    ]
    story.append(make_table(
        ["规则", "内容", "违反示例"],
        rules,
        [PAGE_W*0.12, PAGE_W*0.35, PAGE_W*0.45]
    ))
    story.append(spacer(3))

    # ── 三段论的格和式 ──
    story.append(h3("三段论的格 — 由中项位置决定"))
    ge_data = [
        ["<b>第一格</b>", "大前提主项、小前提谓项", "M—P, S—M → S—P", "<b>法律适用最常用 ⭐</b>"],
        ["第二格", "两前提谓项", "P—M, S—M → S—P", "区别格"],
        ["第三格", "两前提主项", "M—P, M—S → S—P", "例证格"],
        ["第四格", "大前提谓项、小前提主项", "P—M, M—S → S—P", "很少用"],
    ]
    story.append(make_table(
        ["格", "中项位置", "结构", "常用场景"],
        ge_data,
        [PAGE_W*0.12, PAGE_W*0.28, PAGE_W*0.30, PAGE_W*0.22]
    ))
    story.append(spacer(3))

    # ── 省略式 ──
    story.append(h3("三段论的省略式"))
    omit_data = [
        ['<b>省略大前提</b>', '法律依据默认已知', '“你是法人，所以你有民事责任能力”（省略“凡法人都有民事责任能力”）'],
        ['<b>省略小前提</b>', '案件事实不言自明', '“凡法人都应依法纳税，所以该公司应依法纳税”（省略“该公司是法人”）'],
        ['<b>省略结论</b>', '不言而喻', '“凡公民都有肖像权，张三是公民”（省略“张三有肖像权”）'],
    ]
    story.append(make_table(
        ["省略类型", "何时使用", "示例"],
        omit_data,
        [PAGE_W*0.18, PAGE_W*0.22, PAGE_W*0.52]
    ))
    story.append(spacer(3))

    # 逻辑记忆口诀
    story.append(h3("🧠 记忆口诀"))
    tips_lj = [
        "<b>三段论三词项</b> —— 「大P中M小S」：大前提谓项=大项(P)，中间那个=中项(M)，小前提主项=小项(S)",
        "<b>六条规则顺口溜</b> —— 「中周延→词不扩→双否推不出→一否结否→双特推不出→一特结特」",
        "<b>第一格结构</b> —— 「M-P, S-M → S-P」——法律人的肌肉记忆",
        "<b>省略式三型</b> —— 「略大、略小、略结论」——缺什么补什么",
    ]
    for t in tips_lj:
        story.extend(bullet([t], indent=0))
    story.append(spacer(3))

    # 逻辑产出任务
    story.append(h3("✏️ 产出任务"))
    tasks_lj = [
        "闭书画出三段论的三个词项及其位置，并画出第一格的结构图",
        "默写并解释三段论六条规则，用自己编的例子说明每条规则违反时的后果",
        '做一道推理题：“所有法人都是组织，某公司是法人，所以某公司是组织。”——判断这个三段论属于第几格？中项在哪里？是否有效？',
        "找省略式：从《民法典》中找一条法条，将其还原为完整的三段论形式",
    ]
    story.extend(numbered(tasks_lj))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════
    # 第四部分：总结
    # ══════════════════════════════════════════════════════════

    story.extend(h1("📋 今日总产出清单"))

    tasks_all = [
        ["1", "🏛️ 民法", "默写法人定义+四特征", "闭书默写"],
        ["2", "🏛️ 民法", "营利/非营利法人五点对比表", "对比表格"],
        ["3", "🏛️ 民法", "案例分析（董事长个人买画案）", "案例分析"],
        ["4", "⚖️ 刑法", "默写危害结果的四种分类", "闭书默写"],
        ["5", "⚖️ 刑法", "默写因果关系六大特点", "闭书默写"],
        ["6", "⚖️ 刑法", "因果关系辨析判断（医生感染案）", "案例分析"],
        ['7', '刑法', '自编“中断的因果关系”案例', '动手写作'],
        ["8", "🧠 逻辑", "默写三段论三词项+第一格结构", "闭书画图"],
        ["9", "🧠 逻辑", "默写三段论六条规则+自编反例", "闭书默写"],
        ["10", "🧠 逻辑", "判断三段论的格和式（法人推理题）", "练习题"],
        ["11", "🧠 逻辑", "从《民法典》法条还原三段论省略式", "综合应用"],
        ["12", "🧠 逻辑", "（预告）第二节复合命题推理", "明日学习"],
    ]
    story.append(make_table(
        ["序号", "科目", "任务", "类型"],
        tasks_all,
        [PAGE_W*0.08, PAGE_W*0.12, PAGE_W*0.52, PAGE_W*0.20]
    ))
    story.append(spacer(6))

    # ── 跨科串联 ──
    story.append(h3("💡 今日跨科串联"))

    story.append(info_box(
        Paragraph(
            '<font color="#2c5282"><b>\U0001f9f5 \u201c因果关系的逻辑结构\u201d</b></font><br/><br/>'
            '今天三科有一个共同的暗线：<br/><br/>'
            '• <b>逻辑学</b>教的是\u201c三段论\u201d的形式结构：大前提 → 小前提 → 结论<br/>'
            '• <b>刑法学</b>教的是\u201c因果关系\u201d的实质判断：行为是否合乎规律地引起结果<br/>'
            '• <b>民法学</b>教的是\u201c法人责任\u201d的归属规则：谁的行为 → 谁承担后果<br/><br/>'
            '三者的共同结构都是 <b>\u201c原因 → 结果\u201d / \u201c前提 → 结论\u201d</b> 的推理链条。'
            '刑法的因果关系判断本质上就是在运用逻辑的因果推理，'
            '而民法中法定代表人\u201c执行职务\u201d的认定也是因果归属问题。',
            S['body']
        ),
    ))

    story.append(spacer(8))

    # 底部信息
    story.append(hr())
    story.append(Paragraph(
        '📅 Day 7 | 2026-06-08 周一 | 民法第六章~第七章 + 刑法第六章§3-4 + 逻辑第八章§1<br/>'
        '⏱️ 预计用时：民法50min + 刑法50min + 逻辑40min ≈ <b>2.5小时</b>',
        S['body_ni']
    ))
    story.append(spacer(2))
    story.append(Paragraph(
        '📋 质量自检：✔ 章节表格 ✔ 课本原文/法条标记 ✔ 对比表格 ✔ 口诀/记忆技巧 ✔ 具体产出任务 ✔ 跨科串联',
        S['small']
    ))

    # ══════════════════════════════════════════════════════════
    # 构建 PDF
    # ══════════════════════════════════════════════════════════
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=2.2 * cm,
        bottomMargin=1.8 * cm,
        title='Day 7 复习指南 | 法人制度 + 因果关系 + 三段论',
        author='法学考研复习系统',
        subject='民法总论·刑法总论·法律逻辑学',
    )

    doc.build(story, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    print(f"✅ PDF 已生成：{output_pdf}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        input_file = '每日指南/2026-06-08.md'
    else:
        input_file = sys.argv[1]

    output_file = input_file.replace('.md', '.pdf')
    build_pdf(input_file, output_file)
