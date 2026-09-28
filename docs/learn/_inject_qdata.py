# -*- coding: utf-8 -*-
"""把 docs/assets/data/questions.json 注入 docs/learn/index.html 的 <script id="qdata"> 標籤，
讓本機 file:// 雙擊也能開（線上版仍以 fetch 為主，內嵌只是 fallback）。
改規格檔 → build_questions.py → 再跑本腳本一次：PYTHONUTF8=1 python docs/learn/_inject_qdata.py"""
import re, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
html_p = ROOT / "learn" / "index.html"; json_p = ROOT / "assets" / "data" / "questions.json"
data = json.loads(json_p.read_text(encoding="utf-8"))
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
html = html_p.read_text(encoding="utf-8")
new, n = re.subn(r'(<script id="qdata" type="application/json">).*?(</script>)', lambda m: m.group(1) + payload + m.group(2), html, count=1, flags=re.S)
assert n == 1, "找不到 qdata 標籤"
html_p.write_text(new, encoding="utf-8")
print(f"已注入 {data.get('count')} 題（{len(payload):,} 字元）→ {html_p}")
