// ==UserScript==
// @name         Minesweeper Online Helper Overlay
// @namespace    local.minesweeper-helper
// @version      1.0.0
// @description  Shows safe cells, certain mines and mine probabilities on minesweeper.online
// @match        https://minesweeper.online/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Solver (pure, no DOM). Exposed for testing as MSHelperSolver.solve(board).
  //
  // board = { W, H, s: Int8Array(W*H), total }
  //   s[i]: 0..8 = opened number, -1 = closed, -2 = flag, -3 = revealed mine
  //   total: total mines in the game (or null if unknown)
  // returns { p: Float64Array (NaN for non-closed cells), certain: Uint8Array,
  //           approx: Uint8Array, warnings: [] }
  // ---------------------------------------------------------------------------
  const NODE_LIMIT = 2e6;

  function solve(board) {
    const { W, H, s } = board;
    const N = W * H;
    const nb = new Array(N);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const list = [];
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const nx = x + dx, ny = y + dy;
        if (nx >= 0 && ny >= 0 && nx < W && ny < H) list.push(ny * W + nx);
      }
      nb[y * W + x] = list;
    }

    // value[i]: -1 unknown, 0 safe, 1 mine  (for closed/flag cells)
    const value = new Int8Array(N).fill(-1);
    const isNum = (i) => s[i] >= 0;
    const isClosed = (i) => s[i] === -1;
    for (let i = 0; i < N; i++) if (s[i] === -2 || s[i] === -3) value[i] = 1;
    const warnings = [];

    // Constraints: one per number cell that touches closed cells.
    let cons = [];
    for (let i = 0; i < N; i++) {
      if (!isNum(i)) continue;
      let need = s[i];
      const cells = [];
      for (const j of nb[i]) {
        if (value[j] === 1) need--;
        else if (isClosed(j)) cells.push(j);
      }
      if (need < 0 || need > cells.length) {
        warnings.push(`Cell (${i % W},${(i / W) | 0}) is inconsistent — check your flags`);
        continue;
      }
      if (cells.length) cons.push({ cells, need });
    }

    // Trivial propagation: need==0 → all safe; need==len → all mines.
    let changed = true;
    while (changed) {
      changed = false;
      const next = [];
      for (const c of cons) {
        let need = c.need;
        const cells = [];
        for (const j of c.cells) {
          if (value[j] === 1) need--;
          else if (value[j] === -1) cells.push(j);
        }
        if (need < 0 || need > cells.length) { warnings.push('Contradiction found — check your flags'); continue; }
        if (!cells.length) continue;
        if (need === 0 || need === cells.length) {
          for (const j of cells) value[j] = need === 0 ? 0 : 1;
          changed = true;
          continue;
        }
        next.push({ cells, need });
      }
      cons = next;
    }

    // Count known mines and the remaining unknown cells.
    let knownMines = 0;
    for (let i = 0; i < N; i++) if (value[i] === 1) knownMines++;
    const inFrontier = new Uint8Array(N);
    for (const c of cons) for (const j of c.cells) inFrontier[j] = 1;
    const interior = [];
    for (let i = 0; i < N; i++) if (isClosed(i) && value[i] === -1 && !inFrontier[i]) interior.push(i);
    const I = interior.length;
    const M = board.total == null ? null : board.total - knownMines;

    // Split constraints into connected components (union-find on cells).
    const parent = new Map();
    const find = (a) => { while (parent.get(a) !== a) { parent.set(a, parent.get(parent.get(a))); a = parent.get(a); } return a; };
    for (const c of cons) for (const j of c.cells) if (!parent.has(j)) parent.set(j, j);
    for (const c of cons) for (let k = 1; k < c.cells.length; k++) {
      const a = find(c.cells[0]), b = find(c.cells[k]);
      if (a !== b) parent.set(a, b);
    }
    const compMap = new Map();
    for (const c of cons) {
      const r = find(c.cells[0]);
      if (!compMap.has(r)) compMap.set(r, []);
      compMap.get(r).push(c);
    }

    const p = new Float64Array(N).fill(NaN);
    const certain = new Uint8Array(N);
    const approx = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      if (!isClosed(i)) continue;
      if (value[i] !== -1) { p[i] = value[i]; certain[i] = 1; }
    }

    const comps = [];
    for (const ccons of compMap.values()) {
      const res = enumerate(ccons);
      if (res.aborted) {
        // Too large to enumerate: local approximation.
        for (const c of ccons) for (const j of c.cells) {
          const est = c.need / c.cells.length;
          p[j] = isNaN(p[j]) ? est : Math.max(p[j], est);
          approx[j] = 1;
        }
        continue;
      }
      comps.push(res);
    }

    // Combine components with the global mine count.
    const logFact = new Float64Array(N + 2);
    for (let i = 1; i < logFact.length; i++) logFact[i] = logFact[i - 1] + Math.log(i);
    const logC = (n, k) => (k < 0 || k > n) ? -Infinity : logFact[n] - logFact[k] - logFact[n - k];

    const conv = (a, b) => {
      const out = new Float64Array(a.length + b.length - 1);
      for (let i = 0; i < a.length; i++) if (a[i]) for (let j = 0; j < b.length; j++) out[i + j] += a[i] * b[j];
      return out;
    };
    let total = new Float64Array([1]);
    for (const c of comps) total = conv(total, c.Wn);

    // weight(m) for m frontier mines
    let useGlobal = M != null;
    let wLog = null, wMax = -Infinity;
    if (useGlobal) {
      wLog = new Float64Array(total.length);
      for (let m = 0; m < total.length; m++) { wLog[m] = logC(I, M - m); if (total[m] && wLog[m] > wMax) wMax = wLog[m]; }
      if (wMax === -Infinity) { useGlobal = false; warnings.push('Mine count does not fit the board — using local odds'); }
    }
    const weight = (m) => useGlobal ? (m < wLog.length ? Math.exp(wLog[m] - wMax) : Math.exp(logC(I, M - m) - wMax)) : 1;

    let Z = 0;
    for (let m = 0; m < total.length; m++) Z += total[m] * weight(m);

    comps.forEach((c, ci) => {
      let others = new Float64Array([1]);
      comps.forEach((o, oi) => { if (oi !== ci) others = conv(others, o.Wn); });
      const n = c.cells.length;
      const acc = new Float64Array(n);
      for (let k = 0; k < c.Wn.length; k++) {
        if (!c.Wn[k]) continue;
        let f = 0;
        for (let m = 0; m < others.length; m++) if (others[m]) f += others[m] * weight(k + m);
        const wk = c.Wn[k] * f;
        for (let j = 0; j < n; j++) acc[j] += wk * c.P[k][j];
      }
      for (let j = 0; j < n; j++) {
        const cell = c.cells[j];
        const v = Z > 0 ? acc[j] / Z : NaN;
        p[cell] = v;
        if (v < 1e-12) { p[cell] = 0; certain[cell] = 1; }
        else if (v > 1 - 1e-12) { p[cell] = 1; certain[cell] = 1; }
      }
    });

    if (I > 0) {
      let ip;
      if (useGlobal && Z > 0) {
        let e = 0;
        for (let m = 0; m < total.length; m++) e += total[m] * weight(m) * (M - m) / I;
        ip = e / Z;
      } else if (M != null) {
        // rough: expected frontier mines ignored
        let ef = 0, zz = 0;
        for (let m = 0; m < total.length; m++) { ef += total[m] * m; zz += total[m]; }
        ip = Math.min(1, Math.max(0, (M - (zz ? ef / zz : 0)) / I));
      } else ip = NaN;
      for (const i of interior) {
        p[i] = ip;
        if (ip === 0 || ip === 1) certain[i] = 1;
      }
    }

    return { p, certain, approx, warnings, interiorCount: I, minesLeft: M };
  }

  // Enumerate all mine assignments of one component.
  function enumerate(ccons) {
    // order cells by BFS through constraints, so constraints close early
    const cellSet = new Map();
    const cellCons = [];
    const order = [];
    const adj = new Map();
    for (const c of ccons) for (const j of c.cells) { if (!adj.has(j)) adj.set(j, []); adj.get(j).push(c); }
    const seen = new Set();
    const start = ccons[0].cells[0];
    const queue = [start]; seen.add(start);
    while (queue.length) {
      const j = queue.shift();
      order.push(j);
      for (const c of adj.get(j)) for (const k of c.cells) if (!seen.has(k)) { seen.add(k); queue.push(k); }
    }
    order.forEach((j, li) => { cellSet.set(j, li); cellCons.push([]); });
    const need = [], left = [];
    ccons.forEach((c, ci) => {
      need.push(c.need); left.push(c.cells.length);
      for (const j of c.cells) cellCons[cellSet.get(j)].push(ci);
    });

    const n = order.length;
    const assign = new Int8Array(n);
    const Wc = [];
    const S = [];
    let nodes = 0, aborted = false, k = 0;

    (function rec(i) {
      if (aborted) return;
      if (++nodes > NODE_LIMIT) { aborted = true; return; }
      if (i === n) {
        Wc[k] = (Wc[k] || 0) + 1;
        if (!S[k]) S[k] = new Float64Array(n);
        const sk = S[k];
        for (let j = 0; j < n; j++) if (assign[j]) sk[j]++;
        return;
      }
      const cc = cellCons[i];
      for (let v = 0; v <= 1; v++) {
        let ok = true;
        for (const ci of cc) { left[ci]--; need[ci] -= v; }
        for (const ci of cc) if (need[ci] < 0 || need[ci] > left[ci]) { ok = false; break; }
        if (ok) { assign[i] = v; k += v; rec(i + 1); k -= v; }
        for (const ci of cc) { left[ci]++; need[ci] += v; }
        if (aborted) return;
      }
    })(0);

    if (aborted) return { aborted: true };
    let max = 0;
    for (const w of Wc) if (w > max) max = w;
    const Wn = new Float64Array(Wc.length);
    const P = [];
    for (let kk = 0; kk < Wc.length; kk++) {
      if (!Wc[kk]) { P.push(null); continue; }
      Wn[kk] = Wc[kk] / max;
      P.push(S[kk].map((x) => x / Wc[kk]));
    }
    return { cells: order, Wn, P };
  }

  const api = { solve };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }
  if (typeof window === 'undefined') return;
  window.MSHelperSolver = api;
  if (window.__msHelper) { window.__msHelper.toggle(); return; }

  // ---------------------------------------------------------------------------
  // Board reader for minesweeper.online
  // ---------------------------------------------------------------------------
  function readBoard() {
    const els = document.querySelectorAll('div.cell[id^="cell_"]');
    if (!els.length) return null;
    let W = 0, H = 0;
    const items = [];
    for (const el of els) {
      const x = +el.dataset.x, y = +el.dataset.y;
      if (!(x >= 0 && y >= 0)) continue;
      if (x + 1 > W) W = x + 1;
      if (y + 1 > H) H = y + 1;
      items.push([x, y, el]);
    }
    const s = new Int8Array(W * H).fill(-1);
    const el = new Array(W * H);
    let flags = 0;
    for (const [x, y, e] of items) {
      const i = y * W + x;
      el[i] = e;
      const cls = e.className;
      let v = -1;
      if (/_flag\b/.test(cls)) { v = -2; flags++; }
      else if (/_opened\b/.test(cls) || /_type\d+/.test(cls)) {
        const m = cls.match(/_type(\d+)/);
        const t = m ? +m[1] : 0;
        v = t <= 8 ? t : -3; // type 10+ = mines shown after a loss
      } else if (/_closed\b/.test(cls)) v = -1;
      s[i] = v;
    }
    // Mine counter shows "total - flags".
    let total = null;
    const digits = ['100', '10', '1'].map((d) => document.getElementById('top_area_mines_' + d));
    if (digits.every(Boolean)) {
      let val = 0, neg = false, ok = true;
      for (const d of digits) {
        const m = d.className.match(/top-area-num(-|\d)\b/g);
        const last = m && m[m.length - 1].slice(-1);
        if (last === '-') neg = true;
        else if (last != null && /\d/.test(last)) val = val * 10 + +last;
        else ok = false;
      }
      if (ok) total = (neg ? -val : val) + flags;
    }
    if (total == null) {
      const std = { '9x9': 10, '16x16': 40, '30x16': 99 }[W + 'x' + H];
      if (std) total = std;
    }
    const face = document.getElementById('top_area_face');
    const over = (face && /face-(lose|win)\b/.test(face.className)) || s.some((v) => v === -3);
    return { W, H, s, total, el, flags, over };
  }

  // ---------------------------------------------------------------------------
  // Overlay UI
  // ---------------------------------------------------------------------------
  const opts = { on: true, pct: true };
  try { Object.assign(opts, JSON.parse(localStorage.getItem('msHelperOpts') || '{}')); } catch (e) { /* ignore */ }
  const saveOpts = () => { try { localStorage.setItem('msHelperOpts', JSON.stringify(opts)); } catch (e) { /* ignore */ } };

  const style = document.createElement('style');
  style.textContent = `
  #msh-layer{position:absolute;left:0;top:0;pointer-events:none;z-index:9998}
  #msh-layer .msh{position:absolute;box-sizing:border-box;display:flex;align-items:center;justify-content:center;
    font:bold 9px/1 Arial,sans-serif;color:#fff;text-shadow:0 0 2px #000,0 0 2px #000;border-radius:2px}
  #msh-layer .msh.safe{background:rgba(40,200,90,.55);font-size:13px}
  #msh-layer .msh.mine{background:rgba(230,40,40,.6);font-size:13px}
  #msh-layer .msh.best{outline:2px solid #29d3ff;outline-offset:-2px;box-shadow:0 0 6px #29d3ff}
  #msh-layer .msh.approx{font-style:italic}
  #msh-panel{position:fixed;top:10px;right:10px;z-index:9999;background:#1d2227;color:#ddd;border:1px solid #444;
    border-radius:6px;padding:8px 10px;font:12px/1.4 Arial,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.5);min-width:170px}
  #msh-panel b{color:#fff}
  #msh-panel button{background:#333;color:#ddd;border:1px solid #555;border-radius:3px;padding:2px 6px;margin:4px 4px 0 0;cursor:pointer;font-size:11px}
  #msh-panel button.on{background:#2a6f3f;color:#fff}
  #msh-panel .warn{color:#ffb347;max-width:220px}
  #msh-panel .legend span{display:inline-block;width:10px;height:10px;margin:0 3px 0 6px;vertical-align:-1px;border-radius:2px}
  `;
  document.head.appendChild(style);

  const layer = document.createElement('div');
  layer.id = 'msh-layer';
  document.body.appendChild(layer);

  const panel = document.createElement('div');
  panel.id = 'msh-panel';
  panel.innerHTML = `<div><b>Minesweeper helper</b> <span style="opacity:.6">(Alt+H)</span></div>
    <div id="msh-stats">waiting for board…</div>
    <div class="legend"><span style="background:rgba(40,200,90,.8)"></span>safe<span style="background:rgba(230,40,40,.8)"></span>mine<span style="background:none;outline:2px solid #29d3ff"></span>best guess</div>
    <div class="warn" id="msh-warn"></div>
    <button id="msh-on"></button><button id="msh-pct"></button>`;
  document.body.appendChild(panel);
  const $ = (id) => panel.querySelector('#' + id);
  const syncButtons = () => {
    $('msh-on').textContent = opts.on ? 'Overlay: on' : 'Overlay: off';
    $('msh-on').className = opts.on ? 'on' : '';
    $('msh-pct').textContent = opts.pct ? '%: on' : '%: off';
    $('msh-pct').className = opts.pct ? 'on' : '';
  };
  $('msh-on').onclick = () => { opts.on = !opts.on; saveOpts(); syncButtons(); render(true); };
  $('msh-pct').onclick = () => { opts.pct = !opts.pct; saveOpts(); syncButtons(); render(true); };
  syncButtons();

  function color(p) {
    // green (0) → yellow (0.5) → red (1)
    const h = 120 * (1 - p);
    return `hsla(${h},85%,45%,${0.25 + 0.35 * p})`;
  }

  let lastSig = '', lastResult = null, lastBoard = null;

  function render(force) {
    const board = readBoard();
    if (!board) { layer.innerHTML = ''; $('msh-stats').textContent = 'no board on this page'; return; }
    const sig = board.W + 'x' + board.H + ':' + board.total + ':' + board.over + ':' + Array.from(board.s).join(',');
    if (sig !== lastSig) {
      lastSig = sig;
      lastBoard = board;
      try { lastResult = solve(board); } catch (e) { console.error('[msh]', e); lastResult = null; }
      force = true;
    } else {
      lastBoard.el = board.el; // elements may be re-created
    }
    if (!force) { position(); return; }
    draw(lastBoard, lastResult);
  }

  function draw(board, r) {
    layer.innerHTML = '';
    if (board.over) { $('msh-stats').textContent = 'Game over — start a new game.'; $('msh-warn').textContent = ''; return; }
    if (!r) return;
    const { W, H, s } = board;
    let safe = 0, mines = 0, best = Infinity, unknown = 0, opened = 0;
    for (let i = 0; i < W * H; i++) {
      if (s[i] >= 0) opened++;
      if (s[i] !== -1 || isNaN(r.p[i])) continue;
      unknown++;
      if (r.certain[i] && r.p[i] === 0) safe++;
      else if (r.certain[i] && r.p[i] === 1) mines++;
      else if (r.p[i] < best) best = r.p[i];
    }
    const started = opened > 0;
    $('msh-stats').innerHTML = !started ? 'Open a cell to start.' :
      `<b style="color:#5be38a">${safe}</b> safe · <b style="color:#ff6b6b">${mines}</b> sure mines` +
      (safe === 0 && isFinite(best) ? `<br>No safe move — best guess <b>${(best * 100).toFixed(1)}%</b> risk` : '') +
      (board.total != null ? `<br>${r.minesLeft} mines unaccounted` : '<br>(mine total unknown)');
    $('msh-warn').textContent = [...new Set(r.warnings)].join(' · ');
    if (!opts.on || !started) return;

    const frag = document.createDocumentFragment();
    for (let i = 0; i < W * H; i++) {
      if (s[i] !== -1 || isNaN(r.p[i]) || !board.el[i]) continue;
      const p = r.p[i];
      const d = document.createElement('div');
      d.className = 'msh';
      d.dataset.i = i;
      if (r.certain[i] && p === 0) { d.classList.add('safe'); d.textContent = '✓'; }
      else if (r.certain[i] && p === 1) { d.classList.add('mine'); d.textContent = '✖'; }
      else {
        d.style.background = color(p);
        if (r.approx[i]) d.classList.add('approx');
        if (opts.pct) d.textContent = p < 0.995 ? Math.round(p * 100) : '99';
        if (safe === 0 && Math.abs(p - best) < 1e-9) d.classList.add('best');
      }
      frag.appendChild(d);
    }
    layer.appendChild(frag);
    position();
  }

  function position() {
    if (!lastBoard) return;
    for (const d of layer.children) {
      const e = lastBoard.el[+d.dataset.i];
      if (!e) continue;
      const rc = e.getBoundingClientRect();
      d.style.left = rc.left + window.scrollX + 'px';
      d.style.top = rc.top + window.scrollY + 'px';
      d.style.width = rc.width + 'px';
      d.style.height = rc.height + 'px';
    }
  }

  // Poll: cheap, survives the site swapping out the board on new games.
  const timer = setInterval(() => render(false), 250);
  window.addEventListener('resize', position);
  window.addEventListener('scroll', position, true);
  const onKey = (e) => { if (e.altKey && (e.key === 'h' || e.key === 'H')) { opts.on = !opts.on; saveOpts(); syncButtons(); render(true); } };
  document.addEventListener('keydown', onKey);
  render(true);

  window.__msHelper = {
    toggle() { opts.on = !opts.on; saveOpts(); syncButtons(); render(true); },
    remove() {
      clearInterval(timer);
      window.removeEventListener('resize', position);
      window.removeEventListener('scroll', position, true);
      document.removeEventListener('keydown', onKey);
      layer.remove(); panel.remove(); style.remove();
      delete window.__msHelper;
    },
  };
})();
