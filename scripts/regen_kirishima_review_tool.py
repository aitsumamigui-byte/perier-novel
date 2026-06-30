#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regen_kirishima_review_tool.py
perier_kirishima_complete.md の最新版から review_tool_NEW.html を生成する。
霧島版パネル（data-sync="prologue", "ep-1"..）の段落を全話再同期。
"""

import re
import sys
from pathlib import Path

BASE     = Path(__file__).parent / "kirishima"
MD_FILE  = BASE / "perier_kirishima_complete.md"
SRC_HTML = BASE / "review_tool.html"
OUT_HTML = BASE / "review_tool_NEW.html"

# EP番号 → (data-sync値, data-para prefix)
EP_MAP = {
    "prologue": ("prologue",  "prologue-k"),
    "ep1":      ("ep-1",      "ep1-k"),
    "ep2":      ("ep-2",      "ep2-k"),
    "ep3":      ("ep-3",      "ep3-k"),
    "ep4":      ("ep-4",      "ep4-k"),
    "ep5":      ("ep-5",      "ep5-k"),
    "ep6":      ("ep-6",      "ep6-k"),
    "ep7":      ("ep-7",      "ep7-k"),
    "ep8":      ("ep-8",      "ep8-k"),
    "ep9":      ("ep-9",      "ep9-k"),
    "ep10":     ("ep-10",     "ep10-k"),
}


def parse_md(text):
    """
    markdown → {ep_key: [block, ...]}
    block = {"type": "hr"} | {"type": "p", "text": "..."}
    """
    sections = {}
    current_key = None
    current_blocks = []

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # --- プロローグヘッダ ---
        if re.match(r'^##\s*プロローグ', line):
            if current_key is not None:
                sections[current_key] = current_blocks
            current_key = "prologue"
            current_blocks = []
            i += 1
            continue

        # --- EPヘッダ (### EP1: ... など) ---
        m = re.match(r'^###\s*EP(\d+)[：:]', line)
        if m:
            if current_key is not None:
                sections[current_key] = current_blocks
            current_key = f"ep{m.group(1)}"
            current_blocks = []
            i += 1
            continue

        # その他の # ヘッダはスキップ
        if line.startswith("#"):
            i += 1
            continue

        if current_key is None:
            i += 1
            continue

        # --- 区切り線 ---
        if re.match(r'^-{3,}$', line.strip()):
            current_blocks.append({"type": "hr"})
            i += 1
            continue

        # 空行スキップ
        if line.strip() == "":
            i += 1
            continue

        # 段落: 連続する非空行をまとめて1ブロック
        para_lines = []
        while i < len(lines):
            l = lines[i]
            if l.strip() == "" or re.match(r'^-{3,}$', l.strip()) or l.startswith("#"):
                break
            para_lines.append(l.rstrip())
            i += 1

        if para_lines:
            current_blocks.append({"type": "p", "text": "\n".join(para_lines)})

    if current_key is not None:
        sections[current_key] = current_blocks

    return sections


def blocks_to_html(blocks, prefix):
    """ブロックリスト → HTML 文字列"""
    parts = []
    para_idx = 0
    for block in blocks:
        if block["type"] == "hr":
            parts.append('<hr style="border:none;border-top:1px solid #333;margin:10px 0">')
        else:
            text = block["text"]
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            text = text.replace("\n", "<br>")
            parts.append(
                f'<p class="reviewable" data-para="{prefix}-{para_idx}">{text}</p>'
            )
            para_idx += 1
    return "\n".join(parts)


def replace_kiri_panel(html, sync_id, new_inner):
    """
    <div class="panel kiri"> 配下の data-sync="{sync_id}" を持つ .pb div の
    内容を new_inner に置換する（塔馬パネルには触れない）。
    """
    pattern = (
        rf'(<div class="panel kiri">.*?'
        rf'<div class="pb" data-sync="{re.escape(sync_id)}">)'
        rf'(.*?)'
        rf'(</div>\s*</div>)'
    )

    def replacer(m):
        return m.group(1) + "\n" + new_inner + "\n" + m.group(3)

    new_html, count = re.subn(pattern, replacer, html, flags=re.DOTALL)
    if count == 0:
        print(f"  WARN: data-sync='{sync_id}' が霧島パネル内に見つかりません", file=sys.stderr)
    else:
        p_count = new_inner.count('data-para=')
        print(f"  OK  [{sync_id}] {p_count} 段落を再同期")
    return new_html


def main():
    print(f"[1/4] 読込: {MD_FILE.name}")
    md_text = MD_FILE.read_text(encoding="utf-8")

    print(f"[2/4] 読込: {SRC_HTML.name}")
    html = SRC_HTML.read_text(encoding="utf-8")

    print("[3/4] markdown を解析中...")
    sections = parse_md(md_text)
    found = list(sections.keys())
    print(f"      セクション: {found}")

    print("[4/4] 霧島版パネルを置換中...")
    for ep_key, (sync_id, prefix) in EP_MAP.items():
        if ep_key not in sections:
            print(f"  SKIP [{sync_id}] (markdownに未収録)")
            continue
        blocks = sections[ep_key]
        inner_html = blocks_to_html(blocks, prefix)
        html = replace_kiri_panel(html, sync_id, inner_html)

    OUT_HTML.write_text(html, encoding="utf-8")
    size = OUT_HTML.stat().st_size
    print(f"\n完了: {OUT_HTML.name}  ({size:,} bytes / {size/1024:.1f} KB)")
    print("次のステップ:")
    print("  Move-Item kirishima\\review_tool.html kirishima\\review_tool_OLD_backup.html")
    print("  Move-Item kirishima\\review_tool_NEW.html kirishima\\review_tool.html")


if __name__ == "__main__":
    main()
