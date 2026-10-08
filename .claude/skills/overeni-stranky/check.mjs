// Ověření index.html v headless Chromiu: syntaxe skriptu, chyby v konzoli, snímky obrazovky.
// Použití: node .claude/skills/overeni-stranky/check.mjs [--out DIR] [--mobile] [--dark] ["#hash" ...]
// Každý hash (např. "#cas=08:00&pohled=16.6080,49.1950,9000") dá jeden snímek; bez hashe jeden výchozí.
import { createRequire } from 'module';
import { readFileSync, mkdirSync, writeFileSync } from 'fs';
import { execFileSync } from 'child_process';
import path from 'path';
const require = createRequire(import.meta.url);
let pw;
try { pw = require('playwright'); } catch { pw = require(execFileSync('npm', ['root', '-g']).toString().trim() + '/playwright'); }

const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = k => { const i = args.indexOf(k); if (i < 0) return false; args.splice(i, 1); return true; };
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const out = path.resolve(opt('--out') || path.join(root, 'shots'));
const mobile = flag('--mobile'), dark = flag('--dark');
const hashes = args.length ? args : [''];
mkdirSync(out, { recursive: true });

// 1) syntaxe: vytáhne inline <script> a pustí node --check
const html = readFileSync(path.join(root, 'index.html'), 'utf8');
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
const tmp = path.join(out, '_page.js'); writeFileSync(tmp, js);
try { execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' }); console.log('syntaxe: OK'); }
catch (e) { console.log('syntaxe: CHYBA\n' + e.stderr.toString()); process.exit(1); }

// 2) běh v prohlížeči
const browser = await pw.chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const ctx = await browser.newContext({
  viewport: mobile ? { width: 390, height: 844 } : { width: 1440, height: 900 },
  deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile,
  colorScheme: dark ? 'dark' : 'light',
});
await ctx.route(/^https?:\/\//, r => r.abort()); // offline: dlaždice a fonty se nestahují
let errs = 0;
for (const [i, h] of hashes.entries()) {
  const page = await ctx.newPage();
  page.on('pageerror', e => { errs++; console.log('JS chyba:', e.message); });
  page.on('console', m => { if (m.type() === 'error' && !/net::|Failed to load resource/.test(m.text())) { errs++; console.log('console.error:', m.text()); } });
  await page.goto('file://' + path.join(root, 'index.html') + (h && !h.startsWith('#') ? '#' + h : h));
  await page.waitForTimeout(2500);
  const info = await page.evaluate(() => ({ clk: document.getElementById('clk')?.textContent, cnt: document.getElementById('cnt')?.textContent, hash: location.hash }));
  const f = path.join(out, `shot${i + 1}${mobile ? '-mobil' : ''}${dark ? '-tmava' : ''}.png`);
  await page.screenshot({ path: f });
  console.log(`${f}  čas ${info.clk}, vozidel ${info.cnt}, hash ${info.hash || '-'}`);
  await page.close();
}
await browser.close();
console.log(errs ? `CHYB: ${errs}` : 'bez chyb v konzoli');
process.exit(errs ? 1 : 0);
