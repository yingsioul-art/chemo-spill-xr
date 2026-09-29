# -*- coding: utf-8 -*-
"""
把規格檔（唯一內容來源）的 Q1–Qn 解析成 docs/assets/data/questions.json。

用法（任何 session 改完規格檔後跑一次）：
    PYTHONUTF8=1 python tools/build_questions.py
接著 S0 commit + push，GitHub Pages 約 1–2 分鐘後更新。

解析格式（規格檔第三節與 7-1b／7-3b／7-4b）：
    ### 區塊 X｜...            ← 決定 block（A–G）
    **Qn** 題幹
    - A 選項文字 ✓            ← ✓ 標正解
    - B 選項文字
    - 講解-對：...
    - 講解-錯：...
    - 圖：sNNN（...）｜表單 N
<mark ...> 與 </mark> 一律剝掉；題幹後的「＃…」備註另存 note。
每題文字附 sha1 前 8 碼（text_hash），供 S4 的 edge-tts 只重產有改動的音檔。
"""
import re, json, hashlib, sys
from pathlib import Path

SPEC = Path(r"D:/Zettelkasten/20_教學/Makar/20_溢灑XR教材/02_題目與試教/20260929_溢灑XR_需求規格與題目草稿_v1.md")
OUT = Path(__file__).resolve().parent.parent / "docs" / "assets" / "data" / "questions.json"

BLOCK_NAMES = {
    "A": "第一時間反應", "B": "N95 與泡製漂白水", "C": "設置警戒區", "D": "防護裝備與抹布",
    "E": "環境清理", "F": "卸除防護裝備", "G": "再清潔", "H": "紀錄檢討與暴露處置",
}
# 各區塊進哪個型態（使用者 9/29 定架構，見規格檔第二節）
BLOCK_USE = {
    "A": ["learn", "handson", "3d", "test"], "B": ["learn", "test"], "C": ["learn", "handson", "3d", "test"],
    "D": ["learn", "test"], "E": ["handson", "3d", "test"], "F": ["handson", "3d", "test"],
    "G": ["learn_g", "test"], "H": ["learn_g", "test"],
}

def h8(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def parse(text: str):
    text = re.sub(r"<mark[^>]*>|</mark>", "", text)
    lines = text.splitlines()
    block = None
    qs = []
    cur = None
    for ln in lines:
        # 第四節以後（待決定、逆向倒推鏈）不是題庫，停止解析題目
        if re.match(r"^##\s+[四五六七八九]、", ln):
            break
        m = re.match(r"^###\s.*?區塊\s([A-H])", ln)
        if m:
            block = m.group(1); continue
        m = re.match(r"^\*\*Q(\d+)\*\*\s*(.+)$", ln)
        if m:
            if cur: qs.append(cur)
            stem = m.group(2).strip()
            note = ""
            if "＃" in stem:
                stem, note = [x.strip() for x in stem.split("＃", 1)]
            cur = {"id": int(m.group(1)), "block": block, "block_name": BLOCK_NAMES.get(block, ""),
                   "use": BLOCK_USE.get(block, []), "stem": stem, "note": note,
                   "options": [], "answer": None, "explain_ok": "", "explain_ng": "", "img": "", "form_item": ""}
            continue
        if cur is None:
            continue
        m = re.match(r"^-\s+([A-D])\s+(.+?)\s*$", ln)
        if m and not ln.startswith("- 講解") and not ln.startswith("- 圖"):
            txt = m.group(2)
            correct = "✓" in txt
            txt = txt.replace("✓", "").strip()
            cur["options"].append({"key": m.group(1), "text": txt})
            if correct: cur["answer"] = m.group(1)
            continue
        m = re.match(r"^-\s+講解-對：(.+)$", ln)
        if m: cur["explain_ok"] = m.group(1).strip(); continue
        m = re.match(r"^-\s+講解-錯：(.+)$", ln)
        if m: cur["explain_ng"] = m.group(1).strip(); continue
        m = re.match(r"^-\s+圖：(.+?)(?:｜表單\s*(.+))?$", ln)
        if m:
            cur["img"] = m.group(1).strip()
            cur["form_item"] = (m.group(2) or "").strip()
            continue
    if cur: qs.append(cur)
    # 「※教學補充…」是給審題者看的標記，剝出來另存，不進網站文字與音檔
    for q in qs:
        sup = []
        for k in ("explain_ok", "explain_ng"):
            m = re.search(r"\s*※教學補充[：:]?(.*)$", q[k])
            if m:
                sup.append(m.group(1).strip())
                q[k] = q[k][:m.start()].rstrip()
        q["supplement"] = "；".join(x for x in sup if x)
    for q in qs:
        q["text_hash"] = {"ok": h8(q["explain_ok"]), "ng": h8(q["explain_ng"]), "stem": h8(q["stem"])}
    return qs

def validate(qs):
    errs = []
    ids = [q["id"] for q in qs]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        errs.append(f"題號不連續或重複：{ids}")
    for q in qs:
        if not q["block"]: errs.append(f"Q{q['id']} 沒有區塊")
        if not (2 <= len(q["options"]) <= 4): errs.append(f"Q{q['id']} 選項數 {len(q['options'])}")
        if q["answer"] is None: errs.append(f"Q{q['id']} 沒有 ✓ 正解")
        if not q["explain_ok"] or not q["explain_ng"]: errs.append(f"Q{q['id']} 講解缺對版或錯版")
        for k in ("stem", "explain_ok", "explain_ng"):
            if "\\" in q[k] or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", q[k]):
                errs.append(f"Q{q['id']} {k} 含反斜線或控制字元")
    return errs

def parse_reverse(text: str):
    """解析規格檔第五節「逆向工程倒推鏈」→ reverse.json（終點畫面、R 清理主線、D 卸除線、收尾清單、翻正順序）"""
    i = text.find("## 五、")
    if i < 0:
        return None
    sec = text[i:]
    out = {"goal": "", "chains": {"R": [], "D": []}, "checklist": [], "forward": ""}
    part = None
    cur = None
    for ln in sec.splitlines():
        if ln.startswith("### 終點畫面"): part = "goal"; continue
        if ln.startswith("### 倒推鏈 R"): part = "R"; continue
        if ln.startswith("### 倒推鏈 D"): part = "D"; continue
        if ln.startswith("### 收尾檢查清單"): part = "check"; continue
        if ln.startswith("### 翻正後的順序"): part = "fwd"; continue
        if not ln.strip():
            continue
        if part == "goal" and not ln.startswith(">"):
            out["goal"] += ln.strip()
        elif part in ("R", "D"):
            m = re.match(r"^\*\*([RD]\d+)\*\*\s*畫面：(.+?)｜問：(.+)$", ln)
            if m:
                cur = {"id": m.group(1), "scene": m.group(2).strip(), "ask": m.group(3).strip(),
                       "options": [], "answer": None, "explain": "", "form_item": ""}
                out["chains"][part].append(cur); continue
            m = re.match(r"^-\s+([A-D])\s+(.+?)\s*$", ln)
            if cur and m and not ln.startswith("- 講解"):
                t = m.group(2); ok = "✓" in t
                cur["options"].append({"key": m.group(1), "text": t.replace("✓", "").strip()})
                if ok: cur["answer"] = m.group(1)
                continue
            m = re.match(r"^-\s+講解：(.+?)(?:｜表單\s*(.+))?$", ln)
            if cur and m:
                cur["explain"] = m.group(1).strip(); cur["form_item"] = (m.group(2) or "").strip()
                cur["text_hash"] = h8(cur["explain"])
        elif part == "check" and ln.startswith("- "):
            out["checklist"].append(ln[2:].strip())
        elif part == "fwd":
            out["forward"] += ln.strip()
    return out

def validate_reverse(rv):
    errs = []
    for k, chain in rv["chains"].items():
        if not chain: errs.append(f"倒推鏈 {k} 是空的")
        for n in chain:
            if not (2 <= len(n["options"]) <= 4): errs.append(f"{n['id']} 選項數 {len(n['options'])}")
            if n["answer"] is None: errs.append(f"{n['id']} 沒有 ✓ 正解")
            if not n["explain"]: errs.append(f"{n['id']} 沒有講解")
    if not rv["goal"]: errs.append("缺終點畫面")
    return errs

def main():
    text = SPEC.read_text(encoding="utf-8")
    rv = parse_reverse(text)
    if rv:
        rerrs = validate_reverse(rv)
        (OUT.parent / "reverse.json").write_text(json.dumps(rv, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"倒推鏈 → reverse.json：R {len(rv['chains']['R'])} 節點、D {len(rv['chains']['D'])} 節點、收尾清單 {len(rv['checklist'])} 條")
        if rerrs:
            print("⚠️ 倒推鏈檢查未通過："); [print("   -", e) for e in rerrs]; sys.exit(1)
    qs = parse(text)
    errs = validate(qs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": SPEC.name, "count": len(qs), "questions": qs}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for q in qs: by.setdefault(q["block"], []).append(q["id"])
    print(f"解析 {len(qs)} 題 → {OUT}")
    for b in sorted(by): print(f"  區塊 {b} {BLOCK_NAMES.get(b,'')}：Q{by[b][0]}–Q{by[b][-1]}（{len(by[b])} 題）→ {','.join(BLOCK_USE.get(b, []))}")
    if errs:
        print("⚠️ 檢查未通過："); [print("   -", e) for e in errs]; sys.exit(1)
    print("✅ 檢查通過（每題 2–4 選項、恰一正解、對錯講解齊）")

if __name__ == "__main__":
    main()
