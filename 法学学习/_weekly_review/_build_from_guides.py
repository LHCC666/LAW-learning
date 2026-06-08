#!/usr/bin/env python3
"""从 Week 1 每日指南提取知识点，按章重排，生成周总结 MD

用法: python _build_from_guides.py
输出: _weekly_review/民法总论_第一周总结.md + 刑法总论_第一周总结.md
"""

import re, os

GUIDE_DIR = 'D:/ccuurroo/法学学习/每日指南'
OUT_DIR = 'D:/ccuurroo/法学学习/_weekly_review'

# 每日指南 → 对应章节
WEEK1 = {
    '2026-06-01.md': {'civil': '第1章 民法概述', 'criminal': '第1章 刑法概说'},
    '2026-06-02.md': {'civil': '第2章 民法基本原则', 'criminal': '第2章 刑法基本原则'},
    '2026-06-03.md': {'civil': '第3章 民事法律关系\n\n# 第11章 民事权利', 'criminal': '第3章 刑法效力范围'},
    '2026-06-04.md': {'civil': '第5章 自然人（一）', 'criminal': '第4章 犯罪概念与犯罪构成'},
    '2026-06-05.md': {'civil': '第5章 自然人（二）', 'criminal': '第5章 犯罪客体\n\n# 第6章 犯罪客观方面'},
    '2026-06-06.md': {'civil': None, 'criminal': None},  # 复习日
}


def extract_subject_section(content, subject_emoji):
    """从每日指南中提取指定科目的 ## 段落"""
    # 匹配 ## 🏛️ ... 或 ## ⚖️ ... 直到下一个 ## 或文件末尾
    pattern = rf'(## {subject_emoji} .+?)(?=\n## [^#]|\Z)'
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        return ''
    section = m.group(1)

    # 提取 核心知识点精要 部分 —— 兼容多种格式
    # 格式1: ### 🔑 核心知识点精要 (Day 2-5)
    kp = re.search(r'(?:###|####)\s*🔑.*?核心知识点精要\s*\n(.*?)(?=\n###\s+🧠|\n###\s+✏️|\n---\s*\n##|\Z)',
                   section, re.DOTALL)
    if kp:
        return kp.group(1).strip()

    # 格式2: ### 二、核心知识点精要 (Day 1)
    kp = re.search(r'(?:###|####)\s*[二三四五六]、核心知识点精要\s*\n(.*?)(?=\n###\s+[三三四五六]、|\n###\s+🧠|\n###\s+✏️|\n---\s*\n##|\Z)',
                   section, re.DOTALL)
    if kp:
        return kp.group(1).strip()

    # 格式3: ### 🔑 核心回顾 (Day 6 复习日)
    kp = re.search(r'(?:###|####)\s*🔑.*?核心回顾\s*\n(.*?)(?=\n###\s+|$)', section, re.DOTALL)
    if kp:
        return kp.group(1).strip()

    return ''


def clean_content(text):
    """清理格式，适配周总结"""
    lines = text.split('\n')
    result = []
    for line in lines:
        s = line.strip()
        if not s:
            result.append('')
            continue
        # 跳过分隔线
        if s == '---':
            continue
        # 跳过产出任务残留
        if re.match(r'^\d+\.\s*\*\*闭书', s) or re.match(r'^\d+\.\s*\*\*画', s):
            continue
        # 每日指南中 ##### → 周总结中 ####
        if s.startswith('##### '):
            s = '#### ' + s[6:]
        # 每日指南中 #### → 周总结中 ###
        elif s.startswith('#### '):
            s = '### ' + s[5:]
        result.append(s)
    return '\n'.join(result)


def main():
    civil_chapters = {}    # {章名: 内容}
    criminal_chapters = {}

    for fname, mapping in WEEK1.items():
        path = os.path.join(GUIDE_DIR, fname)
        if not os.path.exists(path):
            print(f'  SKIP: {fname} (not found)')
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取民法
        if mapping['civil']:
            civil_text = extract_subject_section(content, '🏛️')
            if civil_text:
                ch = mapping['civil']
                civil_chapters[ch] = clean_content(civil_text)
                print(f'  {fname} → 民法 {ch}: {len(civil_text)} chars')

        # 提取刑法
        if mapping['criminal']:
            criminal_text = extract_subject_section(content, '⚖️')
            if criminal_text:
                ch = mapping['criminal']
                criminal_chapters[ch] = clean_content(criminal_text)
                print(f'  {fname} → 刑法 {ch}: {len(criminal_text)} chars')

    # ── 生成民法 MD ──
    civil_md = [
        '# 民法总论 · 第一周知识点总结',
        '',
        '> 王利明《民法总则（第二版）》| 2026年6月1日—6日 | 基于每日指南整理',
        '',
        '---',
        '',
    ]

    civil_order = [
        '第1章 民法概述',
        '第2章 民法基本原则',
        '第3章 民事法律关系',
        '第11章 民事权利',
        '第5章 自然人（一）',
        '第5章 自然人（二）',
    ]

    for ch in civil_order:
        if ch in civil_chapters:
            # 处理跨章内容（如 第3章 + 第11章 在同一天）
            if '\n\n# ' in ch:
                parts = ch.split('\n\n# ')
                civil_md.append(f'# {parts[0]}')
                civil_md.append('')
                civil_md.append(civil_chapters[ch])
                civil_md.append('')
                civil_md.append(f'# {parts[1]}')
                civil_md.append('')
            else:
                civil_md.append(f'# {ch}')
                civil_md.append('')
                civil_md.append(civil_chapters[ch])
                civil_md.append('')
                civil_md.append('')

    civil_path = os.path.join(OUT_DIR, '民法总论_第一周总结.md')
    civil_text = '\n'.join(civil_md)
    with open(civil_path, 'w', encoding='utf-8') as f:
        f.write(civil_text)
    print(f'\n✅ 民法: {civil_path} ({len(civil_text)} chars)')

    # ── 生成刑法 MD ──
    criminal_md = [
        '# 刑法总论 · 第一周知识点总结',
        '',
        '> 马工程《刑法学（第二版）》上册 | 2026年6月1日—6日 | 基于每日指南整理',
        '',
        '---',
        '',
    ]

    criminal_order = [
        '第1章 刑法概说',
        '第2章 刑法基本原则',
        '第3章 刑法效力范围',
        '第4章 犯罪概念与犯罪构成',
        '第5章 犯罪客体',
        '第6章 犯罪客观方面',
    ]

    for ch in criminal_order:
        if ch in criminal_chapters:
            criminal_md.append(f'# {ch}')
            criminal_md.append('')
            criminal_md.append(criminal_chapters[ch])
            criminal_md.append('')
            criminal_md.append('')

    criminal_path = os.path.join(OUT_DIR, '刑法总论_第一周总结.md')
    criminal_text = '\n'.join(criminal_md)
    with open(criminal_path, 'w', encoding='utf-8') as f:
        f.write(criminal_text)
    print(f'✅ 刑法: {criminal_path} ({len(criminal_text)} chars)')


if __name__ == '__main__':
    main()
