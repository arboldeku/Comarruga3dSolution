// Visor 3D de Comarruga Flood Lab. Solo lee los archivos de docs/CONTRACTS.md (3, 4 y 6).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { parseNpy } from './npy.js';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const BASE = (params.get('base') || '../results').replace(/\/+$/, '');
const WET_M = 0.01; // calado mínimo que se pinta (1 cm)
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const nf = (v, d = 0) => (v == null || !Number.isFinite(Number(v))) ? 'sin dato'
  : Number(v).toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d });
const urlOf = path => `${BASE}/${String(path).split('/').pop()}`; // los contratos dan rutas "results/x": usamos el nombre

// Clases de calado (cm) y de diferencia (cm ahorrados)
const DEPTH_CLASSES = [
  { max: 10, color: '#9be7ff', label: '1 – 10' }, { max: 30, color: '#38b6ff', label: '10 – 30' },
  { max: 50, color: '#1f6fff', label: '30 – 50' }, { max: 100, color: '#5b2be0', label: '50 – 100' },
  { max: Infinity, color: '#e01fd0', label: '> 100' }];
const DIFF_CLASSES = [
  { min: 15, color: '#00e676', label: 'ahorra > 15' }, { min: 5, color: '#7dffb0', label: 'ahorra 5 – 15' },
  { min: 1, color: '#d6ffe6', label: 'ahorra 1 – 5' }, { min: -5, color: '#ffc7a3', label: 'empeora 1 – 5' },
  { min: -Infinity, color: '#ff4b2b', label: 'empeora > 5' }];

const state = { index: null, rain: null, sol: null, mode: 'after', exag: 1, decisions: null, summary: null, hotspotsFile: null };
const cache = new Map(); // scenario_id -> Promise<{result, depth}|{error}>
let dem = null, landuse = null, grid = null, stride = 1, gnx = 0, gny = 0, demMin = 0;
let renderer, scene, camera, controls, world, terrainMesh, waterMesh, markerGroup, updateToken = 0;

function showError(msg) { const b = $('error-band'); b.hidden = false; b.textContent = (b.textContent ? b.textContent + '\n' : '') + msg; }
async function fetchJson(url, optional = false) {
  try {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) { if (optional) return null; throw new Error(`HTTP ${r.status}`); }
    return await r.json();
  } catch (e) { if (optional) return null; throw new Error(`No se pudo leer ${url}: ${e.message}`); }
}
async function fetchNpy(url, expected) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`No se pudo leer ${url}: HTTP ${r.status}`);
  try { return parseNpy(await r.arrayBuffer(), expected); } catch (e) { throw new Error(`${url}: ${e.message}`); }
}

// ---------- escena ----------
function initScene() {
  const canvas = $('c');
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  scene = new THREE.Scene();
  scene.background = new THREE.Color('#05080c');
  camera = new THREE.PerspectiveCamera(45, 1, 1, 1e6);
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2 - 0.02;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8); sun.position.set(-1, 2, 1); scene.add(sun);
  world = new THREE.Group(); scene.add(world);
  markerGroup = new THREE.Group(); scene.add(markerGroup);
  const resize = () => {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe($('canvas-wrap')); resize();
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
}

const vIdx = (r, c) => r * gnx + c;                       // índice de vértice en la malla (posiblemente diezmada)
const cellAt = (r, c) => (r * stride) * grid.nx + c * stride; // índice en el array original

function buildIndex(keepQuad) {
  const idx = [];
  for (let r = 0; r < gny - 1; r++) for (let c = 0; c < gnx - 1; c++) {
    const a = vIdx(r, c), b = vIdx(r, c + 1), d = vIdx(r + 1, c), e = vIdx(r + 1, c + 1);
    if (keepQuad && !keepQuad(a, b, d, e)) continue;
    idx.push(a, d, b, b, d, e);
  }
  return idx;
}

function terrainColor(z01, lu, out) {
  // no urbano: verde-ocre por elevación; urbano: gris; cauce: marrón oscuro. Apagado para que el agua destaque.
  if (lu === 2) out.setRGB(0.36, 0.27, 0.20);
  else if (lu === 1) out.setRGB(0.42 + 0.2 * z01, 0.42 + 0.2 * z01, 0.45 + 0.2 * z01);
  else out.setRGB(0.30 + 0.38 * z01, 0.42 + 0.22 * z01, 0.22 + 0.18 * z01);
}

function buildTerrain() {
  stride = Math.max(1, Math.ceil(Math.sqrt((grid.nx * grid.ny) / 350000)));
  gnx = Math.floor((grid.nx - 1) / stride) + 1; gny = Math.floor((grid.ny - 1) / stride) + 1;
  let mn = Infinity, mx = -Infinity;
  for (const v of dem) if (Number.isFinite(v)) { if (v < mn) mn = v; if (v > mx) mx = v; }
  if (!Number.isFinite(mn)) { mn = 0; mx = 1; }
  demMin = mn; const range = Math.max(mx - mn, 1e-6);
  const pos = new Float32Array(gnx * gny * 3), col = new Float32Array(gnx * gny * 3), c3 = new THREE.Color();
  for (let r = 0; r < gny; r++) for (let c = 0; c < gnx; c++) {
    const i = vIdx(r, c), k = cellAt(r, c), z = Number.isFinite(dem[k]) ? dem[k] : mn;
    pos[i * 3] = c * stride * grid.cell_m; pos[i * 3 + 1] = z - mn; pos[i * 3 + 2] = r * stride * grid.cell_m; // fila 0 = norte = -Z
    terrainColor((z - mn) / range, landuse ? Math.round(landuse[k]) : 0, c3);
    col[i * 3] = c3.r; col[i * 3 + 1] = c3.g; col[i * 3 + 2] = c3.b;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setIndex(buildIndex()); g.computeVertexNormals();
  terrainMesh = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }));
  world.add(terrainMesh);

  const W = (grid.nx - 1) * grid.cell_m, H = (grid.ny - 1) * grid.cell_m, ext = Math.max(W, H);
  state.exag = Math.min(30, Math.max(1, Math.round((0.12 * ext) / range)));
  $('exag').value = state.exag;
  controls.target.set(W / 2, 0, H / 2);
  const far = camera.aspect < 1 ? Math.min(2.2, 0.9 / camera.aspect) : 1; // en vertical (móvil) alejar para que quepa
  camera.position.set(W / 2, ext * 0.65 * far, H / 2 + ext * 0.8 * far);
  camera.near = ext / 2000; camera.far = ext * 20; camera.updateProjectionMatrix();
  controls.maxDistance = ext * 6;
  applyExag();
}

function applyExag() {
  world.scale.y = state.exag;
  $('exag-val').textContent = `×${nf(state.exag, state.exag % 1 ? 1 : 0)}`;
  for (const m of markerGroup.children) m.position.y = m.userData.h * state.exag + m.userData.lift;
}

// Calado en un vértice: máximo del bloque si la malla está diezmada (no perder charcos pequeños)
function sampleDepth(depth, r, c) {
  if (stride === 1) return depth[r * grid.nx + c] || 0;
  let m = 0;
  for (let dr = 0; dr < stride; dr++) for (let dc = 0; dc < stride; dc++) {
    const rr = r * stride + dr, cc = c * stride + dc;
    if (rr < grid.ny && cc < grid.nx) { const v = depth[rr * grid.nx + cc]; if (v > m) m = v; }
  }
  return m;
}

// surface: Float32 por vértice con la altura de lámina (m sobre terreno); value: valor a colorear en cm; show: máscara
function buildWater(depthA, depthB) {
  if (waterMesh) { world.remove(waterMesh); waterMesh.geometry.dispose(); waterMesh.material.dispose(); waterMesh = null; }
  if (!depthA) return;
  const n = gnx * gny, tp = terrainMesh.geometry.attributes.position.array;
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 4), show = new Uint8Array(n), c3 = new THREE.Color();
  const diff = !!depthB;
  for (let r = 0; r < gny; r++) for (let c = 0; c < gnx; c++) {
    const i = vIdx(r, c), a = sampleDepth(depthA, r, c), b = diff ? sampleDepth(depthB, r, c) : 0;
    const h = diff ? Math.max(a, b) : a;
    let vis, hex;
    if (diff) {
      const saved = (a - b) * 100; vis = Math.abs(saved) >= 1;
      hex = (DIFF_CLASSES.find(k => saved >= k.min) || DIFF_CLASSES[DIFF_CLASSES.length - 1]).color;
    } else {
      vis = a > WET_M; hex = DEPTH_CLASSES.find(k => a * 100 <= k.max).color;
    }
    pos[i * 3] = tp[i * 3]; pos[i * 3 + 1] = tp[i * 3 + 1] + (vis ? h : 0) + 0.02; pos[i * 3 + 2] = tp[i * 3 + 2];
    c3.set(hex); col[i * 4] = c3.r; col[i * 4 + 1] = c3.g; col[i * 4 + 2] = c3.b; col[i * 4 + 3] = vis ? 0.9 : 0;
    show[i] = vis ? 1 : 0;
  }
  // los vértices secos de borde heredan el color del vecino mojado para que el degradado de alfa no ensucie el tono
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 4));
  g.setIndex(buildIndex((a, b, d, e) => show[a] | show[b] | show[d] | show[e]));
  waterMesh = new THREE.Mesh(g, new THREE.MeshBasicMaterial({
    vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
  world.add(waterMesh);
}

function makeLabel(text) {
  const cv = document.createElement('canvas'), ctx = cv.getContext('2d'), fs = 44;
  ctx.font = `800 ${fs}px system-ui, Arial`; const w = Math.ceil(ctx.measureText(text).width) + 28;
  cv.width = w; cv.height = fs + 22;
  ctx.font = `800 ${fs}px system-ui, Arial`;
  ctx.fillStyle = '#111'; ctx.fillRect(0, 0, cv.width, cv.height);
  ctx.strokeStyle = '#ffd23f'; ctx.lineWidth = 6; ctx.strokeRect(3, 3, cv.width - 6, cv.height - 6);
  ctx.fillStyle = '#ffd23f'; ctx.textBaseline = 'middle'; ctx.fillText(text, 14, cv.height / 2 + 2);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, sizeAttenuation: true }));
  sp.userData.aspect = cv.width / cv.height; sp.renderOrder = 10;
  return sp;
}

function buildMarkers(hotspots, textFor) {
  for (const m of [...markerGroup.children]) { markerGroup.remove(m); m.material.map?.dispose(); m.material.dispose(); m.geometry?.dispose(); }
  if (!hotspots) return;
  const ext = Math.max(grid.nx, grid.ny) * grid.cell_m, size = ext * 0.035;
  for (const h of hotspots) {
    const cx = Math.min(grid.nx - 1, Math.max(0, Math.round(h.x))), cy = Math.min(grid.ny - 1, Math.max(0, Math.round(h.y)));
    const z = dem[cy * grid.nx + cx], hh = (Number.isFinite(z) ? z : demMin) - demMin;
    const X = cx * grid.cell_m, Z = cy * grid.cell_m;
    const sp = makeLabel(textFor(h)); sp.scale.set(size * sp.userData.aspect, size, 1);
    sp.position.set(X, 0, Z); sp.userData.h = hh; sp.userData.lift = size * 1.6; markerGroup.add(sp);
    const dot = new THREE.Mesh(new THREE.SphereGeometry(size * 0.18, 12, 8), new THREE.MeshBasicMaterial({ color: '#ffd23f', depthTest: false }));
    dot.position.set(X, 0, Z); dot.userData.h = hh; dot.userData.lift = size * 0.2; dot.renderOrder = 9; markerGroup.add(dot);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(size * 0.04, size * 0.04, size * 1.2, 6), new THREE.MeshBasicMaterial({ color: '#ffd23f', depthTest: false }));
    stem.position.set(X, 0, Z); stem.userData.h = hh; stem.userData.lift = size * 0.7; stem.renderOrder = 9; markerGroup.add(stem);
  }
  applyExag();
}

// ---------- datos de escenario ----------
function scenarioEntry(rain, sol) {
  return state.index.scenarios?.find(s => Number(s.rain_mm) === Number(rain) && s.solution_id === sol) || null;
}
function loadScenario(rain, sol) {
  const entry = scenarioEntry(rain, sol), id = entry?.scenario_id || `rain${rain}_${sol}`;
  if (!cache.has(id)) cache.set(id, (async () => {
    if (!entry) return { id, error: `El escenario ${id} no está en index.json (aún no calculado).` };
    try {
      const result = await fetchJson(urlOf(entry.result_file || `${id}.json`));
      const depth = (await fetchNpy(urlOf(result.depth_file || `${id}_depth.npy`), { ny: grid.ny, nx: grid.nx })).data;
      return { id, result, depth, status: result.status || entry.status };
    } catch (e) { return { id, error: e.message }; }
  })());
  return cache.get(id);
}

// ---------- interfaz ----------
function press(container, attr, value) {
  for (const b of container.querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset[attr] === String(value)));
}
function solName(id) { return state.index.solutions?.find(s => s.id === id)?.name || id; }

function buildControls() {
  const rains = state.index.rains_mm?.length ? state.index.rains_mm : [...new Set((state.index.scenarios || []).map(s => s.rain_mm))].sort((a, b) => a - b);
  const sols = state.index.solutions?.length ? state.index.solutions : [...new Set((state.index.scenarios || []).map(s => s.solution_id))].sort().map(id => ({ id, name: id }));
  state.index.solutions = sols;
  $('rain-btns').innerHTML = rains.map(r => `<button data-rain="${esc(r)}">${esc(r)} l/m²</button>`).join('');
  $('sol-btns').innerHTML = sols.map(s => `<button data-sol="${esc(s.id)}">${esc(s.id)}<small>${esc(s.name)}</small></button>`).join('');
  const qr = Number(params.get('rain')), qs = params.get('sol');
  state.rain = rains.includes(qr) ? qr : (rains.includes(60) ? 60 : rains[0]);
  state.sol = sols.some(s => s.id === qs) ? qs : (sols.find(s => s.id !== 'S0')?.id || sols[0]?.id);
  if (['before', 'after', 'diff'].includes(params.get('mode'))) state.mode = params.get('mode');
  $('rain-btns').onclick = e => { const b = e.target.closest('button'); if (b) { state.rain = Number(b.dataset.rain); update(); } };
  $('sol-btns').onclick = e => { const b = e.target.closest('button'); if (b) { state.sol = b.dataset.sol; if (state.mode === 'before') state.mode = 'after'; update(); } };
  $('mode-btns').onclick = e => { const b = e.target.closest('button'); if (b) { state.mode = b.dataset.mode; update(); } };
  $('exag').oninput = e => { state.exag = Number(e.target.value); applyExag(); };
}

function renderLegend(diff) {
  const cls = diff ? DIFF_CLASSES : DEPTH_CLASSES;
  $('legend').innerHTML = `<div class="t">${diff ? 'Diferencia S0 − solución (cm)' : 'Calado máximo (cm)'}</div>` +
    cls.map(k => `<div class="row"><i style="background:${k.color}"></i>${esc(k.label)}</div>`).join('') +
    `<div class="row muted">${diff ? '|dif.| &lt; 1 cm: sin color' : '&lt; 1 cm: sin agua'}</div>`;
}

function statusCell(s) {
  if (!s) return '<span class="muted">sin dato</span>';
  if (s.error) return '<span class="bad">no disponible</span>';
  return s.status === 'invalid' ? '<span class="tag-invalid">INVÁLIDO</span>' : '<span class="ok">válido</span>';
}

function renderKpis(s0, s1) {
  const k0 = s0?.result?.kpis, k1 = s1?.result?.kpis, same = state.sol === 'S0';
  const invalid = [s0, s1].filter(s => s?.status === 'invalid').map(s => s.id);
  $('invalid-flag').hidden = !invalid.length;
  if (invalid.length) $('invalid-flag').textContent = `RESULTADO INVÁLIDO (${[...new Set(invalid)].join(', ')}): error de balance de masa ≥ 5 %. No usar estas cifras.`;
  let hero = '';
  if (k1) {
    let red = '<div class="big muted">—</div><div class="lbl">Reducción frente a S0</div>';
    if (k0 && !same && Number.isFinite(k0.max_depth_cm) && Number.isFinite(k1.max_depth_cm)) {
      const d = k0.max_depth_cm - k1.max_depth_cm, p = k0.max_depth_cm > 0 ? d / k0.max_depth_cm * 100 : null;
      red = `<div class="big ${d >= 0 ? 'ok' : 'bad'}">${d >= 0 ? '−' : '+'}${nf(Math.abs(d), 1)} cm</div>
        <div class="lbl">Calado máx. frente a S0 (${p == null ? 'sin dato' : (d >= 0 ? '−' : '+') + nf(Math.abs(p), 1) + ' %'})</div>`;
    }
    hero = `<div class="kpi-hero"><div><div class="big">${nf(k1.max_depth_cm, 1)} cm</div><div class="lbl">Calado máx. · ${esc(state.sol)}, ${esc(state.rain)} l/m²</div></div><div>${red}</div></div>`;
  }
  const row = (lbl, key, d, unit) => {
    const a = k0?.[key], b = k1?.[key];
    let delta = '—';
    if (!same && Number.isFinite(a) && Number.isFinite(b) && key !== 'volume_error_pct' && key !== 'runtime_s') {
      const dd = b - a; delta = `<span class="${dd <= 0 ? 'ok' : 'bad'}">${dd > 0 ? '+' : dd < 0 ? '−' : ''}${nf(Math.abs(dd), d)}${a > 0 && key !== 'flooded_area_pct' ? ` (${dd > 0 ? '+' : dd < 0 ? '−' : ''}${nf(Math.abs(dd / a * 100), 1)} %)` : ''}</span>`;
    }
    const errBad = key === 'volume_error_pct';
    const cell = v => `<td${errBad && Number.isFinite(v) && Math.abs(v) >= 5 ? ' class="bad"' : ''}>${nf(v, d)}</td>`;
    return `<tr><td>${lbl} <span class="muted">${unit}</span></td>${cell(a)}${cell(b)}<td>${delta}</td></tr>`;
  };
  $('kpis').innerHTML = hero + `<table><thead><tr><th>Indicador</th><th>S0</th><th>${esc(state.sol)}</th><th>Cambio</th></tr></thead><tbody>
    ${row('Calado máx.', 'max_depth_cm', 1, 'cm')}
    ${row('Área inundada', 'flooded_area_m2', 0, 'm²')}
    ${row('Área inundada', 'flooded_area_pct', 2, '%')}
    ${row('Volumen total', 'volume_m3_total', 0, 'm³')}
    ${row('Error balance de masa', 'volume_error_pct', 2, '%')}
    ${row('Tiempo de cálculo', 'runtime_s', 2, 's')}
    <tr><td>Estado</td><td>${statusCell(s0)}</td><td>${statusCell(s1)}</td><td></td></tr></tbody></table>` +
    [s0, s1].filter((s, i) => s?.error && !(i === 1 && same)).map(s => `<p class="bad">${esc(s.error)}</p>`).join('');

  const h0 = s0?.result?.hotspots || [], h1 = s1?.result?.hotspots || [];
  const ids = [...new Set([...h0, ...h1].map(h => h.id))];
  $('hotspots').innerHTML = ids.length ? `<table><thead><tr><th>Punto</th><th>S0 (cm)</th><th>${esc(state.sol)} (cm)</th><th>Ahorro</th></tr></thead><tbody>` +
    ids.map(id => {
      const a = h0.find(h => h.id === id)?.max_depth_cm, b = h1.find(h => h.id === id)?.max_depth_cm;
      const ok = Number.isFinite(a) && Number.isFinite(b), d = ok ? a - b : null;
      return `<tr><td><b>${esc(id)}</b></td><td>${nf(a, 1)}</td><td>${nf(b, 1)}</td><td>${!ok || same ? '—' :
        `<span class="${d >= 0 ? 'ok' : 'bad'}">${d >= 0 ? '−' : '+'}${nf(Math.abs(d), 1)} cm${a > 0 ? ` (${nf(Math.abs(d / a * 100), 0)} %)` : ''}</span>`}</td></tr>`;
    }).join('') + '</tbody></table>' : '<p class="muted">Sin puntos negros en los resultados cargados.</p>';
}

function renderJev() {
  const all = state.decisions, warn = $('jev-warning');
  const live = (all || []).filter(d => d.jev_output && !d.fallback_used);
  const noJev = !all || !all.length || !live.length;
  warn.hidden = !noJev;
  if (noJev) warn.textContent = 'Jev no ejecutado: decisiones del respaldo determinista' +
    (!all ? ' (no se ha encontrado jev_decisions.json).' : !all.length ? ' (jev_decisions.json está vacío).' : '.');
  const j = state.summary?.jev, st = [];
  if (j) {
    const add = (k, lbl, d, u) => { if (j[k] != null) st.push(`<div>${lbl}<br><b>${nf(j[k], d)}${u}</b></div>`); };
    add('accuracy_vs_solver_pct', 'Acierto de Jev frente al solver', 1, ' %');
    add('baseline_accuracy_vs_solver_pct', 'Acierto del respaldo (línea base)', 1, ' %');
    add('latency_p50_ms', 'Latencia p50', 0, ' ms'); add('latency_p95_ms', 'Latencia p95', 0, ' ms');
    add('cost_per_decision_usd', 'Coste por decisión', 5, ' USD'); add('fallback_pct', 'Decisiones con respaldo', 1, ' %');
    add('n_decisions', 'Decisiones registradas', 0, ''); add('n_jev_live', 'Respondidas por Jev', 0, '');
  }
  $('jev-summary').innerHTML = st.length ? `<div class="jev-stats">${st.join('')}</div>` : '';
  if (!all || !all.length) { $('jev-table').innerHTML = ''; return; }
  const rows = all.filter(d => Number(d.rain_mm) === Number(state.rain));
  if (!rows.length) { $('jev-table').innerHTML = `<p class="muted">Sin decisiones registradas para ${esc(state.rain)} l/m².</p>`; return; }
  const mark = v => v === true ? '<span class="ok">✓</span>' : v === false ? '<span class="bad">✗</span>' : '<span class="muted">—</span>';
  $('jev-table').innerHTML = `<table><thead><tr><th>Punto</th><th>Jev</th><th>Probabilidades</th><th>Respaldo</th><th>Mejor (solver)</th></tr></thead><tbody>` +
    rows.map(d => {
      const jo = d.fallback_used ? null : d.jev_output;
      const probs = jo?.probabilities ? Object.entries(jo.probabilities).map(([k, p]) =>
        `<div class="prob${k === jo.choice ? ' sel' : ''}"><span>${esc(k)}</span><span class="bar"><i style="width:${Math.max(0, Math.min(1, Number(p) || 0)) * 100}%"></i></span><span>${nf((Number(p) || 0) * 100, 0)} %</span></div>`).join('') : '<span class="muted">—</span>';
      const jevCell = jo ? `<b>${esc(jo.choice)}</b> ${mark(jo.choice != null && d.solver_best != null ? jo.choice === d.solver_best : d.agree)}${jo.confidence != null ? `<br><span class="muted">conf. ${nf(jo.confidence * 100, 0)} %</span>` : ''}${d.latency_ms != null ? `<br><span class="muted">${nf(d.latency_ms, 0)} ms</span>` : ''}`
        : '<span class="muted">no ejecutado<br>(se usó el respaldo)</span>';
      const fo = d.fallback_output;
      const fbCell = fo ? `<b title="${esc(fo.rule)}">${esc(fo.choice)}</b> ${mark(d.fallback_agree ?? (d.solver_best != null ? fo.choice === d.solver_best : null))}${fo.rule ? `<br><span class="muted">${esc(fo.rule)}</span>` : ''}` : '<span class="muted">sin dato</span>';
      return `<tr><td><b>${esc(d.hotspot_id)}</b></td><td>${jevCell}</td><td class="probs">${probs}</td><td>${fbCell}</td><td><b>${esc(d.solver_best ?? 'sin dato')}</b></td></tr>`;
    }).join('') + '</tbody></table><p class="muted">✓/✗ = coincide o no con la mejor solución según el solver para ese punto negro.</p>';
}

async function update() {
  const token = ++updateToken;
  press($('rain-btns'), 'rain', state.rain); press($('sol-btns'), 'sol', state.sol); press($('mode-btns'), 'mode', state.mode);
  $('mode-btns').querySelector('[data-mode="after"]').textContent = `Después (${state.sol})`;
  $('loading').hidden = false;
  const [s0, s1] = await Promise.all([loadScenario(state.rain, 'S0'), loadScenario(state.rain, state.sol)]);
  if (token !== updateToken) return;
  $('loading').hidden = true;
  const mode = state.mode, shown = mode === 'before' ? s0 : s1;
  let tag;
  if (mode === 'diff') {
    if (s0.depth && s1.depth) { buildWater(s0.depth, s1.depth); tag = `DIFERENCIA: S0 − ${state.sol} · ${state.rain} l/m²`; }
    else { buildWater(null); tag = 'Diferencia no disponible: falta S0 o la solución'; }
  } else {
    buildWater(shown.depth || null);
    tag = shown.depth ? `${mode === 'before' ? 'ANTES' : 'DESPUÉS'}: ${shown === s0 ? 'S0' : state.sol} — ${solName(shown === s0 ? 'S0' : state.sol)} · ${state.rain} l/m²`
      : `Escenario no disponible: ${shown.id}`;
    if (shown.status === 'invalid') tag += ' · INVÁLIDO';
  }
  $('view-tag').textContent = tag;
  renderLegend(mode === 'diff');
  const hs = shown.result?.hotspots || s0.result?.hotspots || state.hotspotsFile?.hotspots;
  const h0 = s0.result?.hotspots || [];
  buildMarkers(hs, h => {
    if (mode === 'diff') { const a = h0.find(x => x.id === h.id)?.max_depth_cm, b = s1.result?.hotspots?.find(x => x.id === h.id)?.max_depth_cm;
      return Number.isFinite(a) && Number.isFinite(b) ? `${h.id} · ${a - b >= 0 ? '−' : '+'}${nf(Math.abs(a - b), 0)} cm` : h.id; }
    return Number.isFinite(h.max_depth_cm) && shown.result ? `${h.id} · ${nf(h.max_depth_cm, 0)} cm` : h.id;
  });
  renderKpis(s0, s1); renderJev();
}

async function main() {
  initScene();
  let index;
  try { index = await fetchJson(`${BASE}/index.json`); }
  catch (e) {
    $('loading').hidden = true; $('dem-badge').textContent = 'Terreno: sin dato';
    showError(`${e.message}\nAún no hay resultados del solver en "${BASE}/". Genera los resultados o abre el visor con ?base=_mock (datos falsos de desarrollo).`);
    $('kpis').innerHTML = '<p class="muted">Sin resultados cargados.</p>';
    state.decisions = null; $('jev-warning').hidden = false; $('jev-warning').textContent = 'Jev no ejecutado: decisiones del respaldo determinista (no hay resultados cargados).';
    return;
  }
  state.index = index; grid = index.grid;
  if (index.label) $('label-badge').textContent = index.label;
  const src = index.dem_source || 'sin dato';
  $('dem-badge').textContent = `Fuente del terreno: ${src}`;
  if (/sint[eé]tico/i.test(src)) { $('synthetic-band').hidden = false; $('dem-badge').classList.add('warn'); }
  $('meta').textContent = `Malla ${grid?.nx} × ${grid?.ny} celdas de ${nf(grid?.cell_m, 1)} m (${grid?.crs || 'CRS sin dato'}) · generado: ${index.generated_at || 'sin dato'} · datos: ${BASE}/`;
  if (BASE.includes('_mock')) showError('DATOS FALSOS DE DESARROLLO (?base=_mock): no proceden del solver.');
  buildControls();

  const [dec, sum, hsf] = await Promise.all([fetchJson(`${BASE}/jev_decisions.json`, true), fetchJson(`${BASE}/kpis_summary.json`, true), fetchJson(`${BASE}/hotspots.json`, true)]);
  state.decisions = Array.isArray(dec) ? dec : Array.isArray(dec?.decisions) ? dec.decisions : null;
  state.summary = sum; state.hotspotsFile = hsf;

  try {
    if (!grid || !(grid.nx > 0) || !(grid.ny > 0) || !(grid.cell_m > 0)) throw new Error('index.json no trae una malla válida (grid.nx, grid.ny, grid.cell_m).');
    dem = (await fetchNpy(urlOf(index.dem_file || 'dem.npy'), { ny: grid.ny, nx: grid.nx })).data;
  } catch (e) { $('loading').hidden = true; showError(`Terreno no disponible: ${e.message}`); renderJev(); return; }
  if (index.landuse_file !== null) {
    try { landuse = (await fetchNpy(urlOf(index.landuse_file || 'landuse.npy'), { ny: grid.ny, nx: grid.nx })).data; }
    catch (e) { console.info('Uso del suelo no disponible (opcional):', e.message); }
  }
  buildTerrain();
  await update();
  window.__viewerReady = true;
}

main().catch(e => { $('loading').hidden = true; showError(`Error inesperado: ${e.message}`); console.error(e); });
