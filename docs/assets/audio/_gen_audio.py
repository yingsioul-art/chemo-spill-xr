# -*- coding: utf-8 -*-
"""溢灑站音檔產生腳本：讀 docs/assets/data/questions.json 的 explain_ok／explain_ng（不從 md 手抄），
用 edge-tts（zh-TW-YunJheNeural，rate -5%，與外滲站相同）產 mp3 到本資料夾。
- 講解音檔命名（與外滲站頁面規則一致）：q01_ok.mp3／q01_ng.mp3 … q27_ok.mp3／q27_ng.mp3
  頁面組路徑：AUD + 'q' + 兩位數題號 + ('_ok'|'_ng') + '.mp3'（learn/index.html qid()）
- 開場旁白：讀 _開場旁白稿.md → intro_home.mp3（首頁）、intro_handson.mp3（③ 情境開場）
- 倒推開場（learn 頁）：reverse.json → rev_goal、rev_R01…R12、rev_D01…D06、rev_forward（見 collect_reverse）
- ⑤ 講解卡：questions.json 若有 "cards": [{"id":"g01","text":...}] 會一併產 g01.mp3…
- _manifest.json 記每檔 hash（題目用 questions.json 的 text_hash；旁白用文字 sha1 前 8 碼）；
  重跑只重產 hash 變動或檔案不存在的檔（--force 全重產）
- 念稿前會做「讀音轉寫」（mL→毫升 等，見 SPEAK_FIX），只影響念法、不影響 hash；
  若改了 SPEAK_FIX 要讓舊檔重念，請加 --force
- 產完重寫 _時長表.md
用法：
  PYTHONUTF8=1 python docs/assets/audio/_gen_audio.py --only q01_ok   # 試聽 1 檔
  PYTHONUTF8=1 python docs/assets/audio/_gen_audio.py                 # 全跑（增量）
  PYTHONUTF8=1 python docs/assets/audio/_gen_audio.py --force         # 全重產
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import time

import edge_tts
from mutagen.mp3 import MP3

HERE = os.path.dirname(os.path.abspath(__file__))
QJSON = os.path.normpath(os.path.join(HERE, "..", "data", "questions.json"))
RJSON = os.path.normpath(os.path.join(HERE, "..", "data", "reverse.json"))  # 倒推鏈（learn 開場）
MANIFEST = os.path.join(HERE, "_manifest.json")
DUR_MD = os.path.join(HERE, "_時長表.md")
INTRO_MD = os.path.join(HERE, "_開場旁白稿.md")
VOICE = "zh-TW-YunJheNeural"
RATE = "-5%"

# 讀音轉寫：畫面文字維持原樣，只改 TTS 念的版本（避免念成英文字母）
SPEAK_FIX = [
    (r"2\s*~\s*3\s*%", "百分之二到三"),
    (r"(\d+)\s*mL", r"\1毫升"),
    (r"(\d+(?:\.\d+)?)\s*gm", r"\1公克"),
    (r"~", "到"),
]


def h8(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def speakable(text):
    for pat, rep in SPEAK_FIX:
        text = re.sub(pat, rep, text)
    return text


def read_intros():
    """讀 _開場旁白稿.md：`## intro_xxx｜用途` 之後到下一個 `## ` 前的段落＝旁白。"""
    if not os.path.exists(INTRO_MD):
        return []
    md = open(INTRO_MD, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"^## (intro_\w+)｜([^\n]+)\n(.*?)(?=^## |\Z)", md, re.S | re.M):
        text = "".join(l.strip() for l in m.group(3).splitlines() if l.strip())
        out.append((f"{m.group(1)}.mp3", text, h8(text), m.group(2).strip()))
    return out


def collect(data):
    """回傳 [(檔名, 文字, hash, 內容摘要)]。"""
    items = []
    for q in sorted(data["questions"], key=lambda x: x["id"]):
        i = q["id"]
        for kind in ("ok", "ng"):
            text = q[f"explain_{kind}"]
            th = (q.get("text_hash") or {}).get(kind) or h8(text)
            items.append((f"q{i:02d}_{kind}.mp3", text, th, f"Q{i}（{q.get('block', '')}）講解-{'對' if kind == 'ok' else '錯'}"))
    for c in data.get("cards", []):
        items.append((f"{c['id']}.mp3", c["text"], c.get("text_hash") or h8(c["text"]), f"⑤ 講解卡 {c['id']}"))
    items += read_intros()
    items += collect_reverse()
    return items


def collect_reverse():
    """倒推鏈音檔（learn 頁開場）：讀 reverse.json
    - rev_R01…rev_R12、rev_D01…rev_D06＝各節點 explain（hash 用 reverse.json 的 text_hash）
    - rev_goal＝終點畫面 goal＋「我們從這裡往回推。」
    - rev_forward＝翻正旁白（由 forward 一行組出：去掉表單項次括號、箭頭改逗號）"""
    if not os.path.exists(RJSON):
        return []
    r = json.load(open(RJSON, encoding="utf-8"))
    out = []
    goal = (r.get("goal") or "").strip()
    if goal:
        t = "終點畫面：" + goal + "我們從這裡往回推。"
        out.append(("rev_goal.mp3", t, h8(t), "倒推・終點畫面旁白"))
    for cname in ("R", "D"):
        for n in r.get("chains", {}).get(cname, []):
            num = int(re.sub(r"\D", "", n["id"]))
            t = n["explain"]
            out.append((f"rev_{cname}{num:02d}.mp3", t, n.get("text_hash") or h8(t), f"倒推 {n['id']} 講解"))
    fw = (r.get("forward") or "").strip()
    if fw:
        steps = [re.sub(r"（[^）]*）", "", s).replace("＋", "和").strip() for s in fw.split("→")]
        t = "把倒推鏈翻正，就是表單的順序：" + "，".join(s for s in steps if s) + "。"
        out.append(("rev_forward.mp3", t, h8(t), "倒推・翻正旁白"))
    return out


async def synth(text, path):
    tts = edge_tts.Communicate(speakable(text), VOICE, rate=RATE)
    await tts.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只產這一檔（不含 .mp3），例如 q01_ok")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    data = json.load(open(QJSON, encoding="utf-8"))
    items = collect(data)
    manifest = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}

    todo = []
    for fname, text, th, label in items:
        if a.only and fname != a.only + ".mp3":
            continue
        path = os.path.join(HERE, fname)
        if not a.force and os.path.exists(path) and manifest.get(fname, {}).get("hash") == th:
            continue
        todo.append((fname, text, th, label))
    print(f"待產 {len(todo)} 檔／共 {len(items)} 檔")

    for fname, text, th, label in todo:
        path = os.path.join(HERE, fname)
        for attempt in range(3):
            try:
                asyncio.run(synth(text, path))
                break
            except Exception as e:  # 網路抖動重試
                print(f"  retry {attempt+1} {fname}: {e}")
                time.sleep(3)
        else:
            print(f"🔴 失敗 {fname}")
            continue
        sec = round(MP3(path).info.length, 1)
        manifest[fname] = {"hash": th, "chars": len(text), "sec": sec, "label": label,
                           "voice": VOICE, "rate": RATE, "generated": time.strftime("%Y-%m-%d %H:%M")}
        print(f"  ✓ {fname:18s} {sec:5.1f}s  {label}")

    # manifest 只保留目前清單內的檔（題號刪減時不留殘影）
    names = {f for f, *_ in items}
    manifest = {k: v for k, v in manifest.items() if k in names}
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    rows = []
    total = 0.0
    for fname, text, th, label in items:
        m = manifest.get(fname)
        if m and os.path.exists(os.path.join(HERE, fname)):
            rows.append(f"| {fname} | {m['sec']} | {m['chars']} | {label} | {m['hash']} |")
            total += m["sec"]
        else:
            rows.append(f"| {fname} | — | {len(text)} | {label}（未產） | {th} |")
    with open(DUR_MD, "w", encoding="utf-8") as f:
        f.write("# 音檔時長表（溢灑站；由 _gen_audio.py 自動重寫）\n\n")
        f.write(f"- 聲音：{VOICE}，rate {RATE}；文字來源＝`docs/assets/data/questions.json` explain_ok／explain_ng＋`reverse.json`（倒推鏈）＋`_開場旁白稿.md`\n")
        f.write(f"- 已產 {sum(1 for r in rows if '（未產）' not in r)} 檔，合計 {total/60:.1f} 分鐘；更新 {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| 檔名 | 秒 | 字數 | 內容 | hash |\n|---|---|---|---|---|\n")
        f.write("\n".join(rows) + "\n")
    print(f"時長表已更新：{len(rows)} 列，合計 {total:.1f} 秒（{total/60:.1f} 分）")


if __name__ == "__main__":
    main()
