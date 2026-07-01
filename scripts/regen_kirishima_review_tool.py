#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regen_kirishima_review_tool.py
perier_kirishima_complete.md の最新版から review_tool_NEW.html を生成する。
霧島版段落ブロックを全話再同期。重複出現があれば2件目以降を削除する。
併せて、ルート index.html（商用公開版・塔馬版）から ep{n}-t-* ブロックも再同期する。
index.html 自体は参照のみで一切変更しない。
"""

import re
import sys
from pathlib import Path

# scripts/ の1つ上がリポジトリルート
ROOT     = Path(__file__).resolve().parent.parent
BASE     = ROOT / "kirishima"
MD_FILE  = BASE / "perier_kirishima_complete.md"
SRC_HTML = BASE / "review_tool.html"
OUT_HTML = BASE / "review_tool_NEW.html"
INDEX_HTML = ROOT / "index.html"

# EP番号 → data-para prefix（霧島版）
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

# EP番号 → data-para prefix（塔馬版、index.html由来）
EP_MAP_T = {f"ep{n}": f"ep{n}-t" for n in range(1, 11)}


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


def _handle_index_p_content(content, entries):
    """index.html の <p>...</p> 中身を段落エントリのリストへ展開する。
    <br> による複数行、<span class="log">...</span> の混在に対応。"""
    for seg in content.split("<br>"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r'^(.*?)<span class="log">(.*?)</span>(.*)$', seg)
        if m:
            before, logtext, after = m.group(1).strip(), m.group(2), m.group(3).strip()
            if before:
                entries.append(before)
            entries.append(logtext)
            if after:
                entries.append(after)
        else:
            entries.append(seg)


def parse_index_html(text):
    """
    ルート index.html（商用公開版・塔馬版）から
    {ep_key: [段落文字列, ...]} を抽出する。参照のみ、index.html は変更しない。
    """
    sections = {}
    for m in re.finditer(r'<section class="episode" id="ep(\d+)">(.*?)</section>', text, re.DOTALL):
        num = str(int(m.group(1)))
        body = m.group(2)

        title_m = re.search(r'<span class="ep-title">(.*?)</span>', body)
        entries = [title_m.group(1)] if title_m else []

        # episode-header は本文抽出対象から除外
        body = re.sub(r'<div class="episode-header">.*?</div>\s*', '', body, flags=re.DOTALL)

        in_dash = False
        for line in body.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line == '<div class="dash-block">':
                in_dash = True
                continue
            if in_dash and line == "</div>":
                in_dash = False
                continue
            if in_dash and line.endswith("</div>"):
                line = line[: -len("</div>")].strip()
                in_dash = False

            dm = re.match(r'^<span class="dash">(.*?)</span>$', line)
            if dm:
                entries.append(dm.group(1))
                continue

            pm = re.match(r'^<p>(.*)</p>$', line)
            if pm:
                _handle_index_p_content(pm.group(1), entries)
                continue

            sm = re.match(r'^<div class="spacer">(.*?)</div>$', line)
            if sm:
                entries.append(sm.group(1))
                continue

            dv = re.match(r'^<div class="divider">(.*?)</div>$', line)
            if dv:
                entries.append(dv.group(1))
                continue

            lg = re.match(r'^<span class="log">(.*?)</span>$', line)
            if lg:
                entries.append(lg.group(1))
                continue

            print(f"  WARN: [ep{num}-t] 未対応の行を検出: {line[:80]}", file=sys.stderr)

        sections[f"ep{num}"] = entries

    return sections


def blocks_to_html_t(entries, prefix):
    """塔馬版(index.html由来)の段落文字列リスト → HTML文字列"""
    parts = []
    for idx, text in enumerate(entries):
        parts.append(f'<p class="reviewable" data-para="{prefix}-{idx}">{text}</p>')
    return "\n".join(parts)


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
    print(f"[1/6] 読込: {MD_FILE.name}")
    md_text = MD_FILE.read_text(encoding="utf-8")

    print(f"[2/6] 読込: {SRC_HTML.name}")
    html = SRC_HTML.read_text(encoding="utf-8")

    print("[3/6] markdown を解析中...")
    sections = parse_md(md_text)
    found = list(sections.keys())
    print(f"      セクション: {found}")

    print("[4/6] 霧島版段落ブロックを置換中...")
    for ep_key, prefix in EP_MAP.items():
        if ep_key not in sections:
            print(f"  SKIP [{prefix}] (markdownに未収録)")
            continue
        blocks = sections[ep_key]
        new_block = blocks_to_html(blocks, prefix)
        html = replace_episode_block(html, prefix, new_block)

    print(f"[5/6] 読込・解析: {INDEX_HTML.name} (塔馬版・参照のみ)")
    index_text = INDEX_HTML.read_text(encoding="utf-8")
    sections_t = parse_index_html(index_text)
    found_t = list(sections_t.keys())
    print(f"      セクション: {found_t}")

    print("[6/6] 塔馬版段落ブロックを置換中...")
    for ep_key, prefix in EP_MAP_T.items():
        if ep_key not in sections_t:
            print(f"  SKIP [{prefix}] (index.htmlに未収録)")
            continue
        entries = sections_t[ep_key]
        new_block = blocks_to_html_t(entries, prefix)
        html = replace_episode_block(html, prefix, new_block)

    OUT_HTML.write_text(html, encoding="utf-8")
    size = OUT_HTML.stat().st_size
    print(f"\n完了: {OUT_HTML.name}  ({size:,} bytes / {size/1024:.1f} KB)")
    print("次のステップ:")
    print("  Move-Item kirishima\\review_tool.html kirishima\\review_tool_OLD_backup.html")
    print("  Move-Item kirishima\\review_tool_NEW.html kirishima\\review_tool.html")


if __name__ == "__main__":
    main()
