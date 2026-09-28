/**
 * 化療藥品溢灑 XR 教材｜前後測成績接收（Web App）v1（2026-09-29）
 * 結構沿用 v2 寫法：欄位「依標題名稱寫入」，標題列缺的欄位自動補在最右邊。
 * 欄位：知識題 Q1–Q27、四組分數、自我效能 SE1–SE11、課程滿意度（V0／V_WHY／V_PREF／OPEN＝開放建議／2D_*／VR_*）。
 * 🔴 這份程式要貼到「溢灑專用」的新試算表（擴充功能 → Apps Script），不要貼進其他教材的試算表。
 * 已有資料可在編輯器執行 backfill() 一次，從「原始JSON」欄回填新欄位。
 */
var SHEET_NAME = 'responses';
var SERVICE = 'spill-test';
var N_Q = 27;                                        // 題數（與 questions.json 一致；題數改了這裡也要改）
var GROUP_KEYS = ['learn', 'clean', 'doff', 'after'];  // 與 index.html 的 GROUPS.key 一致
var GROUP_LABELS = ['自學題', '環境清理', '卸除防護裝備', '再清潔與後續處置'];
var SE_KEYS = ['SE1','SE2','SE3','SE4','SE5','SE6','SE7','SE8','SE9','SE10','SE11'];
var SAT_ITEMS = ['PU1','PU2','EU1','EU2','BI1','A1','R1','R2','C1','S1','M1','M2'];
var SAT_VR_ONLY = ['IM1','IM2'];

function headers_() {
  var h = ['收到時間', '代號', '階段', '開始時間', '送出時間', '作答秒數', '總分', '滿分'];
  for (var g = 0; g < GROUP_LABELS.length; g++) h.push(GROUP_LABELS[g], GROUP_LABELS[g] + '_滿分');
  for (var q = 1; q <= N_Q; q++) h.push('Q' + q + '_答');
  for (var q2 = 1; q2 <= N_Q; q2++) h.push('Q' + q2 + '_對');
  h.push('submission_id', '版本', 'UA', '原始JSON');
  h.push('開放建議', '使用版本', '未用另一版原因', '版本偏好', '自我效能平均');
  SE_KEYS.forEach(function (k) { h.push(k); });
  ['2D', 'VR'].forEach(function (v) {
    SAT_ITEMS.forEach(function (k) { h.push(v + '_' + k); });
    if (v === 'VR') SAT_VR_ONLY.forEach(function (k) { h.push('VR_' + k); });
  });
  return h;
}

function doGet(e) { return json_({ ok: true, service: SERVICE, v: 1, time: new Date().toISOString() }); }

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);                            // 多人同時送出時排隊寫入
    var p = JSON.parse((e && e.postData && e.postData.contents) || '');
    if (!p || !p.code || !p.phase) return json_({ ok: false, error: 'missing code/phase' });
    var sh = getSheet_();
    var hdr = ensureHeaders_(sh);
    if (p.submission_id) {                           // 去重：同一 submission_id 已存在就不再寫
      var idCol = hdr.indexOf('submission_id') + 1, last = sh.getLastRow();
      if (last >= 2) {
        var ids = sh.getRange(2, idCol, last - 1, 1).getValues();
        for (var i = 0; i < ids.length; i++) if (String(ids[i][0]) === String(p.submission_id)) return json_({ ok: true, duplicate: true, row: i + 2 });
      }
    }
    var m = rowMap_(p, true);
    sh.appendRow(hdr.map(function (k) { return m.hasOwnProperty(k) ? m[k] : ''; }));
    return json_({ ok: true, row: sh.getLastRow() });
  } catch (err) {
    return json_({ ok: false, error: String(err && err.message || err) });
  } finally { try { lock.releaseLock(); } catch (x) {} }
}

/** 標題列：空的就整列寫入；已有標題就把缺的欄位補在最右邊（不動既有欄位順序） */
function ensureHeaders_(sh) {
  var want = headers_();
  var lastCol = sh.getLastColumn();
  var have = lastCol ? sh.getRange(1, 1, 1, lastCol).getValues()[0].map(String) : [];
  if (!have.length || have[0] === '') {
    sh.getRange(1, 1, 1, want.length).setValues([want]).setFontWeight('bold'); sh.setFrozenRows(1); return want;
  }
  var add = want.filter(function (k) { return have.indexOf(k) < 0; });
  if (add.length) { sh.getRange(1, have.length + 1, 1, add.length).setValues([add]).setFontWeight('bold'); have = have.concat(add); }
  return have;
}

/** 一筆送出資料 → {欄名: 值} */
function rowMap_(p, withTime) {
  var m = {};
  if (withTime) m['收到時間'] = new Date();
  m['代號'] = "'" + String(p.code).toUpperCase();   // 前導單引號＝文字，保留開頭的 0
  m['階段'] = p.phase_label || p.phase; m['開始時間'] = p.started_at || ''; m['送出時間'] = p.submitted_at || '';
  m['作答秒數'] = p.duration_sec != null ? p.duration_sec : ''; m['總分'] = p.total != null ? p.total : ''; m['滿分'] = p.max != null ? p.max : '';
  var groups = p.groups || {};
  for (var g = 0; g < GROUP_KEYS.length; g++) { var gg = groups[GROUP_KEYS[g]] || {}; m[GROUP_LABELS[g]] = gg.score != null ? gg.score : ''; m[GROUP_LABELS[g] + '_滿分'] = gg.max != null ? gg.max : ''; }
  (p.answers || []).forEach(function (a) { m['Q' + a.id + '_答'] = a.chosen || ''; m['Q' + a.id + '_對'] = a.correct ? 1 : 0; });
  m['submission_id'] = p.submission_id || ''; m['版本'] = p.version || ''; m['UA'] = p.ua || ''; m['原始JSON'] = JSON.stringify(p);
  var se = p.self_efficacy || {};
  SE_KEYS.forEach(function (k) { if (se[k] != null) m[k] = se[k]; });
  if (p.se_mean != null) m['自我效能平均'] = p.se_mean;
  var s = p.satisfaction || {};
  var V0L = { '2d': '只有2D', 'vr': '只有VR', 'both': '兩個都用', 'none': '都沒用' };
  if (s.V0) m['使用版本'] = V0L[s.V0] || s.V0;
  if (s.V_WHY) m['未用另一版原因'] = s.V_WHY;
  if (s.V_PREF) m['版本偏好'] = s.V_PREF;
  if (s.OPEN) m['開放建議'] = s.OPEN;
  Object.keys(s).forEach(function (k) { if (/^(2D|VR)_/.test(k)) m[k] = s[k]; });
  return m;
}

/** 在編輯器手動執行一次：依「原始JSON」回填新欄位（不覆蓋已有值） */
function backfill() {
  var sh = getSheet_(); var hdr = ensureHeaders_(sh); var last = sh.getLastRow();
  if (last < 2) return;
  var rng = sh.getRange(2, 1, last - 1, hdr.length); var vals = rng.getValues();
  var jc = hdr.indexOf('原始JSON'); var n = 0;
  vals.forEach(function (row) {
    var p; try { p = JSON.parse(row[jc]); } catch (e) { return; }
    var m = rowMap_(p, false);
    hdr.forEach(function (k, i) { if ((row[i] === '' || row[i] == null) && m.hasOwnProperty(k) && k !== '代號') { row[i] = m[k]; n++; } });
  });
  rng.setValues(vals); Logger.log('backfilled cells: ' + n);
}

/** 在編輯器手動執行一次可測試寫入（會多一列代號 0000_0101，測完刪掉） */
function testPost() {
  var fake = { submission_id: 'test-' + Date.now(), version: 'manual', code: '0000_0101', phase: 'pre', phase_label: '前測',
    started_at: '2026-09-29T12:00:00+08:00', submitted_at: '2026-09-29T12:10:00+08:00', duration_sec: 600, total: 20, max: 27,
    groups: { learn: { score: 9, max: 11 }, clean: { score: 4, max: 5 }, doff: { score: 3, max: 5 }, after: { score: 4, max: 6 } },
    answers: [], self_efficacy: {}, se_mean: 5, satisfaction: null };
  for (var i = 1; i <= N_Q; i++) fake.answers.push({ id: i, chosen: i % 3 ? 'A' : 'B', correct: i % 3 !== 0 });
  SE_KEYS.forEach(function (k) { fake.self_efficacy[k] = 5; });
  Logger.log(doPost({ postData: { contents: JSON.stringify(fake) } }).getContent());
}

function getSheet_() { var ss = SpreadsheetApp.getActiveSpreadsheet(); return ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME); }
function json_(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
