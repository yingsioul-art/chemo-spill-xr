# -*- coding: utf-8 -*-
"""把 docs/assets/data/questions.json 注入 handson/index.html 的 <script id="qdata"> 標籤，
供雙擊 file:// 開啟時（瀏覽器擋 fetch）當 fallback；線上版仍先走 fetch。
規格檔改了 → 先跑 tools/build_questions.py，再跑本腳本，否則本機開的是舊題。
用法：PYTHONUTF8=1 python docs/handson/_inject_qdata.py
"""
import json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
HTML = HERE / "index.html"
JSON = HERE.parent / "assets" / "data" / "questions.json"

data = json.loads(JSON.read_text(encoding="utf-8"))
# 只塞本站用得到的題目（區塊 A／C／E／F：Q1–Q3、Q6–Q7、Q12–Q21），縮小檔案；supplement 欄不進網頁
IDS = {1, 2, 3, 6, 7, *range(12, 22)}
keep = {**data, "questions": [{k: v for k, v in q.items() if k != "supplement"} for q in data["questions"] if q["id"] in IDS]}
keep["count"] = len(keep["questions"])
payload = json.dumps(keep, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/")

html = HTML.read_text(encoding="utf-8")
pat = re.compile(r'(<script id="qdata" type="application/json">)(.*?)(</script>)', re.S)
assert pat.search(html), "找不到 <script id=\"qdata\"> 標籤"
html = pat.sub(lambda m: m.group(1) + payload + m.group(3), html, count=1)
HTML.write_text(html, encoding="utf-8", newline="\n")
print(f"注入 {keep['count']} 題，{len(payload):,} 字元 → {HTML}")
