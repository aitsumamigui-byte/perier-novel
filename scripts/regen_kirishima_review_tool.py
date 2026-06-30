#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regen_kirishima_review_tool.py
perier_kirishima_complete.md の最新版から review_tool_NEW.html を生成する。
霧島版段落ブロックを全話再同期。重複出現があれば2件目以降を削除する。
"""

import re
import sys
from pathlib import Path

# scripts/ の1つ上がリポジトリルート
BASE     = Path(__file__).resolve().parent.parent / "kirishima"
MD_FILE  = BASE / "perier_kirishima_complete.md"
SRC_HTML = BASE / "review_tool.html"
OUT_HTML = BASE / "review_tool_NEW.html"

# EP番号 → data-para prefix
EP_MAP = {
    "prologue": "prologue-k",
    "ep1":      "ep1-k",
    "ep2":      "ep2-k",
    "ep3":      "ep3-k",
    "ep4":      "ep4-k",
    "ep5":      "ep5-k",
    "ep6":      "ep6-k",
    "ep7":      "ep7-k",
    "ep8":      "ep8-k",
    "ep9":      "ep9-k",
    "ep10":     "ep10-k",
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

        # 1行 = 1段落ブロック（1文1行整形済みMD対応）
        current_blocks.append({"type": "p", "text": line.rstrip()})
        i += 1

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


def replace_episode_block(html, prefix, new_block):
    """
    data-para="{prefix}-数字" を持つ <p class="reviewable"> の連続ブロックを
    re.finditer で全件検出し、最初の出現を new_block に置換、
    2件目以降は空文字列で削除する。
    インデックスのズレを防ぐため後ろから前に向かって処理する。
    """
    single_p = (
        rf'<p class="reviewable" data-para="{re.escape(prefix)}-\d+">.*?</p>'
    )
    # 連続ブロック: 段落の間に <hr> と空白のみ許容
    block_pat = (
        rf'(?:{single_p})'
        rf'(?:\s*(?:<hr[^>]*>)?\s*(?:{single_p}))*'
    )

    matches = list(re.finditer(block_pat, html, flags=re.DOTALL))

    if not matches:
        print(f"  WARN: [{prefix}] ブロック未検出", file=sys.stderr)
        return html

    spans = [(m.start(), m.end()) for m in matches]
    result = html
    removed = 0

    # 後ろから前へ：2件目以降を削除
    for i in range(len(spans) - 1, 0, -1):
        start, end = spans[i]
        result = result[:start] + result[end:]
        removed += 1

    # 1件目を new_block に置換
    start, end = spans[0]
    result = result[:start] + new_block + result[end:]

    p_count = new_block.count('data-para=')
    dup_msg = f", {removed}件重複削除" if removed else ""
    print(f"  OK  [{prefix}] {p_count}段落{dup_msg}")
    return result


def main():
    print(f"[1/4] 読込: {MD_FILE.name}")
    md_text = MD_FILE.read_text(encoding="utf-8")

    print(f"[2/4] 読込: {SRC_HTML.name}")
    html = SRC_HTML.read_text(encoding="utf-8")

    print("[3/4] markdown を解析中...")
    sections = parse_md(md_text)
    found = list(sections.keys())
    print(f"      セクション: {found}")

    print("[4/4] 霧島版段落ブロックを置換中...")
    for ep_key, prefix in EP_MAP.items():
        if ep_key not in sections:
            print(f"  SKIP [{prefix}] (markdownに未収録)")
            continue
        blocks = sections[ep_key]
        new_block = blocks_to_html(blocks, prefix)
        html = replace_episode_block(html, prefix, new_block)

    OUT_HTML.write_text(html, encoding="utf-8")
    size = OUT_HTML.stat().st_size
    print(f"\n完了: {OUT_HTML.name}  ({size:,} bytes / {size/1024:.1f} KB)")
    print("次のステップ:")
    print("  Move-Item kirishima\\review_tool.html kirishima\\review_tool_OLD_backup.html")
    print("  Move-Item kirishima\\review_tool_NEW.html kirishima\\review_tool.html")


if __name__ == "__main__":
    main()
