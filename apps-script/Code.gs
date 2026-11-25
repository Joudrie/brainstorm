/**
 * Vice City Reel Queue backend. Lives inside the "Vice City Reel Queue" Google Sheet
 * (Extensions → Apps Script) and is deployed as a web app.
 *
 * Script properties (Project Settings → Script properties):
 *   IG_TOKEN  the Meta access token for @vicecitytop (never put it in this file)
 *   PIN       the posting PIN people type on the website
 *
 * The sheet's first tab keeps one row per reel:
 *   A Posted (TRUE/FALSE) | B # | C Day | D Reel link | E Notes | F Queue | G Post link | H Error | I Posted at
 */
const IG_USER = '17841466601675122';               // @vicecitytop
const GRAPH = 'https://graph.facebook.com/v21.0';
const VIDEO_PREFIX = 'https://joudrie.github.io/brainstorm/videos/';
const HEADERS = ['Posted', '#', 'Day', 'Reel', 'Notes', 'Queue', 'Post link', 'Error', 'Posted at'];

function sheet_() {
  const sh = SpreadsheetApp.getActive().getSheets()[0];
  const head = sh.getRange(1, 1, 1, HEADERS.length).getValues()[0];
  if (head[5] !== 'Queue') sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  return sh;
}

function idOf_(link) {
  const m = String(link || '').match(/\/(?:reel|reels|p)\/([A-Za-z0-9_-]+)/);
  return m ? m[1] : '';
}

function rows_() {
  const sh = sheet_();
  const last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, HEADERS.length).getValues().map((v, i) => ({
    row: i + 2, id: idOf_(v[3]), posted: v[0] === true || String(v[0]).toUpperCase() === 'TRUE',
    n: v[1], queue: Number(v[5]) || null, postUrl: v[6] || '', error: v[7] || '',
  })).filter(r => r.id);
}

// Find the reel's row, adding one if it isn't in the sheet yet.
function rowFor_(id, n, url) {
  const hit = rows_().find(r => r.id === id);
  if (hit) return hit.row;
  const sh = sheet_();
  sh.appendRow([false, n || '', '', url || ('https://www.instagram.com/reel/' + id + '/'), '', '', '', '', '']);
  return sh.getLastRow();
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return json_({ ok: true, rows: rows_().map(r => ({ id: r.id, posted: r.posted, queue: r.queue, postUrl: r.postUrl, error: r.error })) });
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'Bad request' }); }
  const props = PropertiesService.getScriptProperties();
  if (!body.pin || body.pin !== props.getProperty('PIN')) return json_({ ok: false, error: 'Wrong PIN' });

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return json_({ ok: false, error: 'Busy, try again in a moment' });
  try {
    const sh = sheet_();
    if (body.action === 'check') {
      const row = rowFor_(body.id, body.n, body.url);
      sh.getRange(row, 1).setValue(!!body.posted);
      if (body.posted) sh.getRange(row, 8).setValue('');
      return json_({ ok: true });
    }
    if (body.action === 'order') {
      const ids = (body.ids || []).slice(0, 2000);
      const byId = {}; rows_().forEach(r => { byId[r.id] = r.row; });
      ids.forEach((id, i) => { const row = byId[id] || rowFor_(id); sh.getRange(row, 6).setValue(i + 1); });
      return json_({ ok: true });
    }
    if (body.action === 'post') return json_(post_(sh, body, props.getProperty('IG_TOKEN')));
    return json_({ ok: false, error: 'Unknown action' });
  } finally {
    lock.releaseLock();
  }
}

function graph_(method, path, params, token) {
  const opts = { method: method, muteHttpExceptions: true };
  let url = GRAPH + '/' + path;
  params = Object.assign({}, params, { access_token: token });
  if (method === 'get') url += '?' + Object.keys(params).map(k => k + '=' + encodeURIComponent(params[k])).join('&');
  else opts.payload = params;
  const res = UrlFetchApp.fetch(url, opts);
  const data = JSON.parse(res.getContentText() || '{}');
  if (data.error) throw new Error(data.error.message || 'Instagram error');
  return data;
}

function post_(sh, body, token) {
  if (!token) return { ok: false, error: 'IG_TOKEN is not set in Script properties' };
  if (!/^[A-Za-z0-9_-]+$/.test(body.id || '')) return { ok: false, error: 'Bad reel id' };
  const video = String(body.videoUrl || '');
  if (video.indexOf(VIDEO_PREFIX) !== 0) return { ok: false, error: 'Video must come from the reel queue site' };
  const row = rowFor_(body.id, body.n, body.url);
  const already = sh.getRange(row, 1).getValue();
  if (already === true || String(already).toUpperCase() === 'TRUE') return { ok: false, error: 'Already posted' };
  try {
    const c = graph_('post', IG_USER + '/media', { media_type: 'REELS', video_url: video,
      caption: String(body.caption || '').slice(0, 2200), share_to_feed: 'true' }, token);
    let status = '';
    for (let i = 0; i < 50; i++) {                    // up to ~4 minutes for Instagram to process
      status = graph_('get', c.id, { fields: 'status_code' }, token).status_code;
      if (status === 'FINISHED') break;
      if (status === 'ERROR' || status === 'EXPIRED') throw new Error('Instagram could not process the video');
      Utilities.sleep(5000);
    }
    if (status !== 'FINISHED') throw new Error('Instagram is still processing. Try again in a few minutes');
    const p = graph_('post', IG_USER + '/media_publish', { creation_id: c.id }, token);
    const link = graph_('get', p.id, { fields: 'permalink' }, token).permalink || '';
    sh.getRange(row, 1).setValue(true);
    sh.getRange(row, 7, 1, 3).setValues([[link, '', new Date()]]);
    return { ok: true, postUrl: link };
  } catch (err) {
    sh.getRange(row, 8).setValue(String(err.message || err).slice(0, 300));
    return { ok: false, error: String(err.message || err) };
  }
}
