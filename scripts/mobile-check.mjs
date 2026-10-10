// Loads every HTML page at 390px and checks that the document does not
// scroll sideways and that the console stays quiet.
// Usage: node scripts/mobile-check.mjs [baseURL]
// Default baseURL is http://127.0.0.1:8765. Requires Chrome with
// --remote-debugging-port=9222.
import { readdirSync, statSync } from 'fs';
import { join } from 'path';

const base = (process.argv[2] || 'http://127.0.0.1:8765').replace(/\/$/, '');
const root = new URL('..', import.meta.url).pathname;
function pages(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    if (name === '.git' || name === 'node_modules') continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) pages(p, acc);
    else if (name.endsWith('.html')) acc.push(p.slice(root.length - 1));
  }
  return acc;
}
const list = pages(root).sort();
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

const created = await (await fetch('http://127.0.0.1:9222/json/new?about:blank', { method: 'PUT' })).json();
const ws = new WebSocket(created.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
let id = 0;
const pending = new Map();
const logs = [];
ws.addEventListener('message', ev => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
    else p.resolve(msg.result);
  } else if (msg.method === 'Runtime.exceptionThrown') {
    const d = msg.params.exceptionDetails;
    logs.push((d.exception?.description || d.text || 'exception').slice(0, 300));
  } else if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
    logs.push((msg.params.args || []).map(a => a.value || a.description || '').join(' ').slice(0, 300));
  } else if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
    logs.push(msg.params.entry.text.slice(0, 300));
  }
});
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const msgId = ++id;
  pending.set(msgId, { resolve, reject });
  ws.send(JSON.stringify({ id: msgId, method, params }));
});
await send('Page.enable');
await send('Runtime.enable');
await send('Log.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: 390, height: 844, deviceScaleFactor: 1, mobile: true,
});

const fail = [];
for (const page of list) {
  logs.length = 0;
  await send('Page.navigate', { url: base + page });
  let ready = false;
  for (let i = 0; i < 50; i++) {
    const ev = await send('Runtime.evaluate', { expression: 'document.readyState', returnByValue: true });
    if (ev.result?.value === 'complete') { ready = true; break; }
    await sleep(100);
  }
  await sleep(60);
  const measured = await send('Runtime.evaluate', {
    expression: `(() => {
      const de = document.documentElement;
      const sw = Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0);
      return { sw, vw: de.clientWidth };
    })()`,
    returnByValue: true,
  });
  const m = measured.result?.value || {};
  const errs = logs.filter(x => !/favicon|ERR_FILE_NOT_FOUND/i.test(x));
  const overflow = !(m.vw > 0 && m.sw <= m.vw + 1);
  if (!ready || overflow || errs.length) {
    fail.push({ page, ready, sw: m.sw, vw: m.vw, errs: errs.slice(0, 3) });
    console.log('FAIL', page, m.sw, m.vw, errs[0] || '');
  } else {
    console.log('ok', page);
  }
}
ws.close();
if (fail.length) {
  console.error(fail.length + ' page(s) failed');
  process.exit(1);
}
console.log('pass', list.length, 'pages at 390px');
