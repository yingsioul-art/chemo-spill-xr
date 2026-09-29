# -*- coding: utf-8 -*-
"""把 docs/assets/data/questions.json 注入 docs/learn/index.html 的 <script id="qdata"> 標籤，
並把 docs/assets/data/reverse.json（倒推鏈）注入 <script id="rdata"> 標籤，
讓本機 file:// 雙擊也能開（線上版仍以 fetch 為主，內嵌只是 fallback）。
改規格檔 → build_questions.py → 再跑本腳本一次：PYTHONUTF8=1 python docs/learn/_inject_qdata.py"""
import re, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
html_p = ROOT / "learn" / "index.html"
html = html_p.read_text(encoding="utf-8")


def inject(html, tag_id, json_p):
    data = json.loads(json_p.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")
    pat = r'(<script id="' + tag_id + r'" type="application/json">).*?(</script>)'
    new, n = re.subn(pat, lambda m: m.group(1) + payload + m.group(2), html, count=1, flags=re.S)
    assert n == 1, f"找不到 {tag_id} 標籤"
    return new, data, payload


html, q, qp = inject(html, "qdata", ROOT / "assets" / "data" / "questions.json")
html, r, rp = inject(html, "rdata", ROOT / "assets" / "data" / "reverse.json")
html_p.write_text(html, encoding="utf-8")
nodes = sum(len(v) for v in r.get("chains", {}).values())
print(f"已注入 {q.get('count')} 題（{len(qp):,} 字元）＋倒推鏈 {nodes} 節點（{len(rp):,} 字元）→ {html_p}")
