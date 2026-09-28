# 溢灑前後測成績回傳｜Google Apps Script 部署步驟

> 目的：學員在 `docs/test/index.html` 送出後，成績以 JSON POST 到 Apps Script Web App，寫進**溢灑專用**的 Google 試算表一列。
> 全程約 10 分鐘，需要您本人 Google 登入（AI 不代做）。做完把 Web App 網址貼回 `index.html` 檔頭的 `ENDPOINT` 常數再 push。
>
> 🔴 **一定要新建一份試算表＋新的 Apps Script 專案**，不要沿用外滲那份，否則兩個教材的成績會混在一起。
>
> 目前狀態（2026-09-29）：`ENDPOINT = ""`（未連線）。學員送出時畫面顯示「試算表尚未連線，已存在本機」，作答暫存在學員瀏覽器的 localStorage `spill_test_local`，不會送到任何地方。

## 一、建試算表

1. Google 雲端硬碟 → 新增 → **Google 試算表**，命名例如 `溢灑XR_前後測成績`。
2. 不用建欄位或工作表；程式第一次收到資料時會自動建 `responses` 工作表與標題列。

## 二、貼程式碼

1. 在該試算表：**擴充功能 → Apps Script**（開新分頁，專案已綁定這份試算表）。
2. 左側 `Code.gs` 內容全部刪掉，貼上本資料夾 **`_Code_v2.gs`** 的全文。
3. 按 💾 儲存（Ctrl+S）。專案名稱例如 `溢灑XR成績`。
4. （可選）上方函式下拉選 `testPost` → 執行，第一次會要求授權；試算表多出一列代號 `0000_0101` 即成功，**測完刪掉那一列**。

## 三、部署為 Web App

1. 右上 **部署 → 新增部署作業**。
2. 左上齒輪 → 類型選 **網頁應用程式**。
3. 設定：
   - 說明：`v1`
   - 執行身分：**我**
   - 誰可以存取：**任何人**（學員不會登入 Google，一定要選這個）
4. 按 **部署** → 授權：選您的帳號 →「Google 尚未驗證這個應用程式」→ 進階 → 前往（專案名稱）（不安全）→ 允許。
5. 複製 **網頁應用程式網址**（形如 `https://script.google.com/macros/s/AKfycb…/exec`）。
6. 瀏覽器直接開該網址（GET），看到 `{"ok":true,"service":"spill-test",...}` 代表部署成功（`service` 必須是 `spill-test`，若是別的就是貼錯專案）。

## 四、貼回網頁

1. 開 `C:\dev\chemo-spill-xr\docs\test\index.html`，找到檔頭：
   ```js
   const ENDPOINT = "";
   ```
   改成
   ```js
   const ENDPOINT = "https://script.google.com/macros/s/AKfycb…/exec";
   ```
2. commit＋push；Pages 約 1–2 分鐘更新。

## 五、測試

1. 開 `…/chemo-spill-xr/test/`，手機末 4 碼填 `0000`、生日填 `0101`、選前測，作答到送出。
2. 成績頁下方應顯示「成績已送出 ✅（試算表第 N 列）」。
3. 回試算表確認多一列。**正式試教前把測試列刪掉**。

## 六、之後改程式碼

- 改了 Code.gs 要 **部署 → 管理部署作業 → 編輯（鉛筆）→ 版本選「新版本」→ 部署**，網址不變；只按儲存不會生效。
- 若改成「新增部署作業」，網址會變，要重新貼回 `ENDPOINT`。

## 七、試算表欄位（程式自動建）

| 欄 | 內容 |
|---|---|
| 收到時間 | 伺服器收到的時間 |
| 代號 | 手機末 4 碼＋`_`＋生日月日（存成文字，保留開頭的 0） |
| 階段 | 前測／後測 |
| 開始時間、送出時間、作答秒數 | 學員端時間 |
| 總分、滿分 | 答對題數／27 |
| 自學題、環境清理、卸除防護裝備、再清潔與後續處置 | 各組得分（滿分另欄）；分組＝題庫 block A–D／E／F／G–H |
| Q1_答 … Q27_答 | 學員選的選項代號（**JSON 原始代號，正解一律是 A**；畫面上選項順序已隨機） |
| Q1_對 … Q27_對 | 1＝答對、0＝答錯 |
| submission_id、版本、UA、原始JSON | 去重與除錯用 |
| 開放建議 | 後測選填意見 |
| 使用版本、未用另一版原因、版本偏好 | 後測滿意度分流題 |
| 自我效能平均、SE1 … SE11 | 0–10 分，SE11＝壓力情境題 |
| 2D_PU1 … 2D_M2、VR_PU1 … VR_M2、VR_IM1、VR_IM2 | 後測滿意度 1–5 分（依學員用過的版本才有值） |

## 八、網頁端送出方式（給除錯看）

- `fetch(ENDPOINT, {method:'POST', headers:{'Content-Type':'text/plain;charset=utf-8'}, body: JSON})`：簡單請求不觸發 CORS 預檢；Apps Script 302 轉址，fetch 自動跟隨讀到 `{ok:true,row:N}`。
- 讀不到回應時自動改 `mode:'no-cors'` 再送一次（伺服器以 `submission_id` 去重），並提供「重新送出成績」鈕。
- localStorage key（全部 `spill_` 前綴）：
  - `spill_test:<代號>:<pre|post>` 作答進度
  - `spill_test_lastcode` 上次代號
  - `spill_test_pending` 送出失敗待重送
  - `spill_test_local` ENDPOINT 空白時的本機暫存
  - `spill_xrprog`（各站共用進度物件的 `pre`／`post` 欄）與 `spill_test_pre_done`／`spill_test_post_done`：首頁進度用的完成旗標
