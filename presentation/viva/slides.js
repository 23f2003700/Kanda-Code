/* Kanda Code viva deck — slide builders. Each builder gets (slide element, paused timeline, step)
   and must call step() once per click. Everything drawn comes from window.KC (data.js). */
(() => {
  const KC = window.KC;
  const SPK = ['#EDB94E', '#E2834F', '#E583B8', '#7DCB6E', '#6FBCDD'];
  const C = { gold: '#EDB94E', copper: '#E2834F', pink: '#E583B8', green: '#7DCB6E', red: '#EC6461', sky: '#6FBCDD',
              plum: '#B4407F', plumd: '#5B1A45', muted: '#B9A8B3', dim: '#7F6D79', ink: '#F7EFF4', slate: '#9C8F98' };
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const SEASON = MON.slice(3);                       // Apr..Dec
  const n = (v, d = 0) => Number(v).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });
  const lakh = (t) => (t / 1e5).toFixed(1);
  const pct = (d) => (d * 100).toFixed(1) + '%';
  const mname = (ym) => MON[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* ---------- bind numbers from KC into the markup ---------- */
  const ev = (expr) => Function('KC', 'n', 'lakh', 'pct', 'mname', 'return (' + expr + ')')(KC, n, lakh, pct, mname);
  $$('[data-v]').forEach((el) => { el.textContent = ev(el.dataset.v); });
  $$('[data-count]').forEach((el) => { el.dataset.to = ev(el.dataset.count); el.textContent = '0'; });

  /* ---------- project mark, team lists, QR ---------- */
  const MARK_COL = ['#E8A98C', '#B4407F', '#E2834F', '#8E2F5E', '#E2834F', '#B4407F'];
  const markSvg = () => '<svg viewBox="0 0 100 100">' +
    [46, 38.5, 31, 23.5, 16, 9].map((r, i) => `<circle class="ring" cx="50" cy="50" r="${r}" fill="none" stroke="${MARK_COL[i]}" stroke-width="${i ? 4 : 5}"/>`).join('') +
    '<circle class="core" cx="50" cy="50" r="5" fill="#EDB94E"/></svg>';
  $$('[data-mark]').forEach((el) => { el.innerHTML = markSvg(); });
  const teamHtml = () => KC.team.map((t, i) =>
    `<div class="mem"><span class="d" style="background:${SPK[i]};box-shadow:0 0 12px ${SPK[i]}"></span><div><b>${t.name}</b><span>${t.roll} · ${t.part}</span></div></div>`).join('');
  $('#team').innerHTML = teamHtml(); $('#team2').innerHTML = teamHtml();
  try {
    const q = qrcode(0, 'M'); q.addData(KC.repo); q.make();
    $('#qr').innerHTML = q.createSvgTag({ cellSize: 8, margin: 0, scalable: true });
    const p = $('#qr svg path'); if (p) p.setAttribute('fill', '#1D1420');
  } catch (e) { $('#qr').textContent = KC.repo; }

  /* ---------- animation helpers ---------- */
  // SVG children keep their own transform attribute (axes, groups), so they only fade; HTML also rises
  const isSvg = (t) => { const a = gsap.utils.toArray(t); return a.length && a.every((e) => e instanceof SVGElement && e.tagName !== 'svg'); };
  const fadeUp = (tl, t, at, o = {}) => isSvg(t)
    ? tl.fromTo(t, { autoAlpha: 0 }, { autoAlpha: 1, duration: o.d ?? .6, stagger: o.st ?? .08, ease: 'power1.out' }, at)
    : tl.fromTo(t, { autoAlpha: 0, y: o.y ?? 26 },
      { autoAlpha: 1, y: 0, duration: o.d ?? .6, stagger: o.st ?? .08, ease: o.ease ?? 'power3.out' }, at);
  const fadeOut = (tl, t, at, o = {}) => tl.to(t, { autoAlpha: 0, y: o.y ?? -20, duration: o.d ?? .4, ease: 'power2.in' }, at);
  const header = (tl, el) => {
    fadeUp(tl, $('.hd .kicker', el), 0, { y: 14 });
    tl.fromTo($('.hd h2', el), { autoAlpha: 0, y: 34, clipPath: 'inset(0 0 100% 0)' },
      { autoAlpha: 1, y: 0, clipPath: 'inset(0 0 0% 0)', duration: .8, ease: 'power3.out' }, .08);
  };
  const countUp = (tl, el, to, at, o = {}) => {
    const obj = { v: o.from ?? 0 }, f = o.f ?? ((v) => n(v, o.dec ?? 0));
    el.textContent = f(obj.v);
    tl.to(obj, { v: +to, duration: o.d ?? 1.3, ease: 'power2.out', onUpdate: () => { el.textContent = f(obj.v); } }, at);
  };
  const legend = (el) => $$('.legend', el);

  /* ---------- D3 chart scaffolding ---------- */
  let clipN = 0;
  function chart(id, m = { l: 80, r: 30, t: 30, b: 60 }) {
    const host = document.getElementById(id);
    const W = parseFloat(host.style.width), H = parseFloat(host.style.height);
    const svg = d3.select(host).append('svg').attr('width', W).attr('height', H).attr('viewBox', `0 0 ${W} ${H}`);
    const defs = svg.append('defs');
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);
    return { host, svg, defs, g, W, H, m, w: W - m.l - m.r, h: H - m.t - m.b };
  }
  function clip(c, pad = 40) {
    const id = 'clip' + (clipN++);
    const r = c.defs.append('clipPath').attr('id', id).append('rect')
      .attr('x', -pad).attr('y', -pad - 40).attr('width', 0).attr('height', c.h + 2 * pad + 80);
    return { url: `url(#${id})`, rect: r.node(), full: c.w + 2 * pad };
  }
  const reveal = (tl, cl, at, d = 1.4, ease = 'power1.inOut') =>
    tl.fromTo(cl.rect, { attr: { width: 0 } }, { attr: { width: cl.full }, duration: d, ease }, at);
  const yAxis = (c, y, fmt, ticks = 5) => c.g.append('g').attr('class', 'axis grid')
    .call(d3.axisLeft(y).ticks(ticks).tickSize(-c.w).tickFormat(fmt)).call((a) => a.select('.domain').remove())
    .call((a) => a.selectAll('text').attr('x', -14));
  const xAxis = (c, x, fmt) => c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.h})`)
    .call(d3.axisBottom(x).tickSize(0).tickPadding(16).tickFormat(fmt)).call((a) => a.select('.domain').attr('stroke', 'rgba(255,255,255,.2)'));
  const axisTitle = (c, text, x, y, anchor = 'start') => c.g.append('text').attr('class', 'lbl-m').attr('x', x).attr('y', y)
    .attr('text-anchor', anchor).text(text);

  /* ---------- three.js helpers ---------- */
  const GLS = window.GLS = [];
  function GL(hostId, fov = 35) {
    const host = document.getElementById(hostId);
    const w = parseFloat(host.style.width), h = parseFloat(host.style.height);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x000000, 0);
    host.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(fov, w / h, .1, 400);
    const g = { host, renderer, scene, camera, w, h, slide: host.closest('.slide'), update: null,
      resize() { const k = Math.min((window.STAGE_SCALE || 1) * (window.devicePixelRatio || 1), 2);
        renderer.setPixelRatio(1); renderer.setSize(Math.max(2, Math.round(w * k)), Math.max(2, Math.round(h * k)), false); } };
    g.resize(); GLS.push(g); return g;
  }
  function loop(ms) {
    const t = ms / 1000;
    for (const g of GLS) {
      const v = g.slide.style.visibility;
      if (v && v !== 'hidden') { if (g.update) g.update(t); g.renderer.render(g.scene, g.camera); }
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  function label(text, o = {}) {
    const fs = o.size ?? 64, pad = 18, font = `${o.weight ?? 700} ${fs}px ${o.family ?? 'Manrope, Segoe UI, sans-serif'}`;
    const cv = document.createElement('canvas'), cx = cv.getContext('2d');
    cx.font = font; const tw = cx.measureText(text).width;
    cv.width = Math.ceil(tw + pad * 2); cv.height = Math.ceil(fs * 1.45 + pad);
    cx.font = font; cx.textBaseline = 'middle'; cx.textAlign = 'center';
    if (o.bg) { cx.fillStyle = o.bg; const r = cv.height / 2; cx.beginPath(); cx.roundRect?.(0, 0, cv.width, cv.height, r); cx.fill(); }
    cx.fillStyle = o.color ?? '#F7EFF4'; cx.fillText(text, cv.width / 2, cv.height / 2 + 2);
    const tex = new THREE.CanvasTexture(cv); tex.minFilter = THREE.LinearFilter;
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: o.depthTest ?? true, opacity: o.opacity ?? 1 });
    const sp = new THREE.Sprite(mat); const hgt = o.h ?? .5;
    sp.scale.set(hgt * cv.width / cv.height, hgt, 1); return sp;
  }
  function dotTexture() {
    const cv = document.createElement('canvas'); cv.width = cv.height = 64; const cx = cv.getContext('2d');
    const gr = cx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.35, 'rgba(255,255,255,.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    cx.fillStyle = gr; cx.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(cv);
  }
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const easeOutBack = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const easeOut = (x) => 1 - Math.pow(1 - x, 3);

  /* ---------- the 3D onion (title + thanks) ---------- */
  function onionScene(hostId, o = {}) {
    const g = GL(hostId, 32);
    g.renderer.localClippingEnabled = true;
    const { scene, camera } = g;
    camera.position.set(4.6, 2.2, 6.2); camera.lookAt(0, .15, 0);
    scene.add(new THREE.AmbientLight(0xffffff, .45));
    const key = new THREE.DirectionalLight(0xffe0b0, 1.25); key.position.set(4, 6, 5); scene.add(key);
    const rim = new THREE.DirectionalLight(0xff6fb5, 1.1); rim.position.set(-5, 2, -4); scene.add(rim);
    const core = new THREE.PointLight(0xffb84a, 2.2, 5); core.position.set(.2, 0, .2); scene.add(core);

    const pA = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
    const pB = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
    const planes = [pA, pB];
    const prof = [];
    for (let i = 0; i <= 72; i++) {
      const th = i / 72 * Math.PI; let r = Math.sin(th) * 1.06, y = -Math.cos(th);
      if (y > 0) { r *= 1 - .38 * Math.pow(y, 2.2); y *= 1 + .42 * Math.pow(y, 3); } else { y *= .9; }
      prof.push(new THREE.Vector2(Math.max(r, .002), y));
    }
    const geo = new THREE.LatheGeometry(prof, 120);
    const onion = new THREE.Group(); scene.add(onion);
    const shells = [];
    const LAY = [
      { s: 1.00, c: '#B4552F', in: '#E8B48A' },  // dry outer skin
      { s: .86, c: '#8E2F5E', in: '#F3DDE8' },
      { s: .72, c: '#A3366C', in: '#F6E6EE' },
      { s: .58, c: '#B4407F', in: '#F7EAF1' },
      { s: .44, c: '#C2508D', in: '#FAF0F5' },
      { s: .30, c: '#D0649D', in: '#FCF5F8' },
    ];
    LAY.forEach((L, i) => {
      [[L.c, 1], [L.in, .955]].forEach(([col, k], j) => {
        const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color(col), roughness: j ? .7 : .45, metalness: .05,
          side: THREE.DoubleSide, clippingPlanes: planes, clipIntersection: true, transparent: true, opacity: 1,
          emissive: new THREE.Color(j ? '#3a1d2a' : col), emissiveIntensity: j ? .25 : .12 });
        const m = new THREE.Mesh(geo, mat); m.userData = { base: L.s * k, i }; onion.add(m); shells.push(m);
      });
    });
    const coreBall = new THREE.Mesh(new THREE.SphereGeometry(.13, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0xffc35a })); onion.add(coreBall);
    // veins on the dry skin
    const vg = new THREE.BufferGeometry(), vp = [];
    for (let k = 0; k < 28; k++) {
      const a = k / 28 * Math.PI * 2;
      for (let i = 0; i < prof.length - 1; i++) {
        const p0 = prof[i], p1 = prof[i + 1], s = 1.004;
        vp.push(Math.cos(a) * p0.x * s, p0.y, Math.sin(a) * p0.x * s, Math.cos(a) * p1.x * s, p1.y, Math.sin(a) * p1.x * s);
      }
    }
    vg.setAttribute('position', new THREE.Float32BufferAttribute(vp, 3));
    const veins = new THREE.LineSegments(vg, new THREE.LineBasicMaterial({ color: 0x7a3f1c, transparent: true, opacity: .45,
      clippingPlanes: planes, clipIntersection: true }));
    onion.add(veins);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(.03, .07, .45, 16),
      new THREE.MeshStandardMaterial({ color: 0x9a5a2c, roughness: .8 }));
    stem.position.y = 1.55; onion.add(stem);
    // dust
    const N = 900, pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
    const pal = [new THREE.Color('#EDB94E'), new THREE.Color('#E583B8'), new THREE.Color('#E2834F'), new THREE.Color('#ffffff')];
    for (let i = 0; i < N; i++) {
      const r = 2.4 + Math.random() * 5, a = Math.random() * Math.PI * 2, y = (Math.random() - .5) * 6;
      pos.set([Math.cos(a) * r, y, Math.sin(a) * r], i * 3);
      const c = pal[i % 4]; col.set([c.r, c.g, c.b], i * 3);
    }
    const pg = new THREE.BufferGeometry();
    pg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pg.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const dust = new THREE.Points(pg, new THREE.PointsMaterial({ size: .07, map: dotTexture(), vertexColors: true, transparent: true,
      opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    scene.add(dust);

    const st = { open: 0, cut: 0, dust: 0 };
    g.state = st;
    onion.rotation.z = -.12;
    g.update = (t) => {
      onion.rotation.y = t * .22;
      onion.position.y = Math.sin(t * .9) * .06;
      shells.forEach((m) => {
        const k = easeOutBack(clamp01(st.open * 1.6 - m.userData.i * .12));
        m.scale.setScalar(Math.max(.0001, k * m.userData.base));
      });
      veins.scale.setScalar(Math.max(.0001, easeOutBack(clamp01(st.open * 1.6))));
      stem.scale.setScalar(Math.max(.0001, clamp01(st.open * 1.6 - .3)));
      coreBall.scale.setScalar(Math.max(.0001, clamp01(st.cut * 1.2)) * (1 + .08 * Math.sin(t * 3)));
      const a = st.cut * Math.PI * .62 + .0001;          // opening angle of the cut wedge (world space)
      const ca = Math.cos(onion.rotation.y * 0), sa = 0;
      pA.normal.set(Math.sin(-.75), 0, -Math.cos(-.75)).normalize();
      pB.normal.set(-Math.sin(a - .75), 0, Math.cos(a - .75)).normalize();
      dust.rotation.y = -t * .03; dust.material.opacity = st.dust * .85;
    };
    return g;
  }

  /* =================================================================== SLIDES */
  const SL = window.SLIDES = {};

  /* ---------- 1 · title ---------- */
  SL.title = (el, tl, step) => {
    const g = onionScene('gl-title');
    tl.fromTo(g.state, { open: 0 }, { open: 1, duration: 2.2, ease: 'none' }, 0)
      .fromTo(g.state, { cut: 0 }, { cut: 1, duration: 1.4, ease: 'power2.inOut' }, 1.3)
      .fromTo(g.state, { dust: 0 }, { dust: 1, duration: 1.6 }, .4);
    fadeUp(tl, $$('.logos > *', el), .1, { st: .1 });
    tl.fromTo($$('.logos .ring', el), { strokeDasharray: 300, strokeDashoffset: 300 }, { strokeDashoffset: 0, duration: 1.1, stagger: .07, ease: 'power2.out' }, .3);
    fadeUp(tl, $('.inst', el), .55);
    tl.fromTo($$('.t1 .w', el), { autoAlpha: 0, y: 70, rotationX: -60, transformOrigin: '50% 100%' },
      { autoAlpha: 1, y: 0, rotationX: 0, duration: .9, stagger: .09, ease: 'power3.out' }, .7);
    fadeUp(tl, $('.sub', el), 1.25);
    fadeUp(tl, $$('.mem', el), 1.45, { st: .07 });
    step();
  };

  /* ---------- 2 · problem ---------- */
  SL.problem = (el, tl, step) => {
    header(tl, el);
    const c = chart('c-season', { l: 70, r: 20, t: 50, b: 50 });
    const x = d3.scaleBand(MON, [0, c.w]).padding(.22), y = d3.scaleLinear([0, 1.75], [c.h, 0]);
    yAxis(c, y, (d) => d.toFixed(1) + '×', 4); xAxis(c, x, (d) => d);
    const avg = c.g.append('g');
    avg.append('line').attr('x1', 0).attr('x2', c.w).attr('y1', y(1)).attr('y2', y(1)).attr('stroke', 'rgba(255,255,255,.45)').attr('stroke-dasharray', '6 8');
    const col = d3.scaleSequential([0.5, 1.6], d3.interpolateRgbBasis(['#5B1A45', '#B4407F', '#E2834F', '#EDB94E']));
    const bars = c.g.selectAll('rect.b').data(KC.season).join('rect').attr('class', 'b')
      .attr('x', (d) => x(d.m)).attr('width', x.bandwidth()).attr('y', (d) => y(d.p)).attr('height', (d) => y(0) - y(d.p))
      .attr('rx', 6).attr('fill', (d) => d.m === 'Apr' ? C.red : col(d.p));
    const apr = KC.season[3], nov = KC.season[10];
    const tag = (d, txt, fill) => c.g.append('text').attr('class', 'lbl').attr('x', x(d.m) + x.bandwidth() / 2)
      .attr('y', y(d.p) - 16).attr('text-anchor', 'middle').attr('fill', fill).style('font-size', '30px').style('font-weight', 800).text(txt);
    const tA = tag(apr, apr.p.toFixed(2) + '×', C.red), tN = tag(nov, nov.p.toFixed(2) + '×', C.gold);
    const x0 = x('Apr') + x.bandwidth() / 2, x1 = x('Nov') + x.bandwidth() / 2;
    const arc = c.g.append('path').attr('d', `M${x0},${y(apr.p) - 56} C${x0 + 60},${y(1.95)} ${x1 - 80},${y(1.95)} ${x1},${y(nov.p) - 72}`)
      .attr('fill', 'none').attr('stroke', C.gold).attr('stroke-width', 3).attr('stroke-dasharray', '2 9').attr('stroke-linecap', 'round');
    const arcL = c.g.append('text').attr('class', 'lbl').attr('x', (x0 + x1) / 2).attr('y', y(1.86)).attr('text-anchor', 'middle').attr('fill', C.gold)
      .text(`+${Math.round(KC.eda.median_rise)}% median · Nov > Apr in ${KC.eda.years_nov_above_apr} of ${KC.eda.years} years`);
    fadeUp(tl, [c.svg.selectAll('.axis').nodes(), avg.node()].flat(), .2, { st: .05 });
    tl.fromTo(bars.nodes(), { scaleY: 0, transformOrigin: '50% 100%' }, { scaleY: 1, duration: .7, stagger: .05, ease: 'back.out(1.4)' }, .35);
    tl.fromTo([tA.node(), tN.node()], { autoAlpha: 0, scale: .4, transformOrigin: '50% 100%' }, { autoAlpha: 1, scale: 1, duration: .5, stagger: .15, ease: 'back.out(2)' }, 1.1);
    const L = arc.node().getTotalLength();
    tl.fromTo(arc.node(), { strokeDashoffset: L, strokeDasharray: `${L} ${L}` }, { strokeDashoffset: 0, duration: .9, ease: 'power2.inOut' }, 1.4)
      .set(arc.node(), { strokeDasharray: '2 9' });
    fadeUp(tl, [arcL.node(), legend(el)[0]], 1.9);
    fadeUp(tl, '#pb-paid', 2.1);
    step();
    // rot rows
    const onion = (fill) => `<svg viewBox="0 0 42 50"><path d="M21 3C23 11 38 18 38 32C38 42 30 48 21 48C12 48 4 42 4 32C4 18 19 11 21 3Z" fill="${fill}"/><path d="M21 14C16 22 15 31 16 46M21 14C26 22 27 31 26 46" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="1.5"/></svg>`;
    ['#on-chawl', '#on-cold'].forEach((id) => { $(id).innerHTML = Array.from({ length: 10 }, () => onion('#C2508D')).join(''); });
    fadeUp(tl, '#pb-rot', '+=0');
    tl.fromTo($$('#pb-rot .onions svg'), { autoAlpha: 0, scale: .3 }, { autoAlpha: 1, scale: 1, duration: .4, stagger: .025, ease: 'back.out(2)' }, '<.2');
    const rotted = $$('#on-chawl svg').slice(4);           // 5.5 of 10 rot (54.9%)
    tl.to(rotted.map((s) => s.querySelector('path')), { fill: '#4A2B22', duration: .5, stagger: .1 }, '+=.15')
      .to(rotted, { scale: .78, autoAlpha: .45, y: 6, duration: .5, stagger: .1 }, '<');
    tl.to($$('#on-chawl svg')[4], { autoAlpha: .7, scale: .9, y: 2, duration: .3 }, '>-.3');
    tl.to($$('#on-cold svg')[9].querySelector('path'), { fill: '#7a4b55', duration: .5 }, '<')
      .to($$('#on-cold svg')[9], { autoAlpha: .75, scale: .93, duration: .5 }, '<');
    step();
    tl.fromTo('#pb-q', { autoAlpha: 0, y: 30, boxShadow: '0 0 0 0 rgba(237,185,78,0)' },
      { autoAlpha: 1, y: 0, boxShadow: '0 0 60px -6px rgba(237,185,78,.45)', duration: .7, ease: 'power3.out' });
    step();
  };

  /* ---------- 3 · approach ---------- */
  SL.approach = (el, tl, step) => {
    header(tl, el);
    const ICON = {
      data: '<ellipse cx="28" cy="13" rx="17" ry="6"/><path d="M11 13v30c0 3.3 7.6 6 17 6s17-2.7 17-6V13"/><path d="M11 28c0 3.3 7.6 6 17 6s17-2.7 17-6"/>',
      wave: '<path d="M4 38C12 38 13 14 22 14S31 42 40 42 50 22 52 18"/><path d="M4 48h48" opacity=".4"/>',
      fc: '<path d="M6 48h44"/><path d="M8 40l10-11 9 6 10-14"/><path d="M38 21l12-9" stroke-dasharray="3 5"/>',
      lp: '<rect x="7" y="8" width="17" height="17" rx="4"/><rect x="32" y="8" width="17" height="17" rx="4"/><rect x="19.5" y="33" width="17" height="17" rx="4"/><path d="M15.5 25v4h25v-4M28 29v4"/>',
      ok: '<circle cx="28" cy="28" r="20"/><path d="M19 29l6 6 12-14"/>',
      pin: '<path d="M28 51s16-15 16-27a16 16 0 0 0-32 0c0 12 16 27 16 27z"/><circle cx="28" cy="24" r="6"/>',
    };
    const NODES = [
      ['data', 'Data', `${n(KC.dq.rows_all_india)} records`, 0],
      ['wave', 'Pattern', 'seasonality + H1', 1],
      ['fc', 'Forecast', `${KC.forecast.methods.length} models compared`, 2],
      ['lp', 'Plan', 'LP: sell or store', 3],
      ['ok', 'Backtest', `${KC.backtest.years.length} unseen seasons`, 3],
      ['pin', 'All-India', `${KC.ai.markets} markets`, 4],
    ];
    const pipe = $('#pipe'), gap = (1680 - 230) / 5;
    const line = d3.select(pipe).append('svg').attr('width', 1680).attr('height', 120).style('position', 'absolute').style('left', 0).style('top', 0);
    const ln = line.append('line').attr('x1', 115).attr('x2', 1680 - 115).attr('y1', 56).attr('y2', 56)
      .attr('stroke', 'rgba(255,255,255,.22)').attr('stroke-width', 3).attr('stroke-dasharray', '4 10').node();
    NODES.forEach(([ic, b, s, who], i) => {
      const d = document.createElement('div'); d.className = 'node'; d.style.left = (i * gap) + 'px'; d.style.setProperty('--c', SPK[who]);
      d.innerHTML = `<div class="ic"><svg viewBox="0 0 56 56">${ICON[ic]}</svg></div><b>${b}</b><span>${s}</span><i>${KC.team[who].name.split(' ')[0]}</i>`;
      pipe.appendChild(d);
    });
    tl.fromTo(ln, { attr: { x2: 115 } }, { attr: { x2: 1680 - 115 }, duration: 1.2, ease: 'power2.inOut' }, .3);
    tl.fromTo($$('.node', pipe), { autoAlpha: 0, y: 40, scale: .9 }, { autoAlpha: 1, y: 0, scale: 1, duration: .6, stagger: .14, ease: 'back.out(1.6)' }, .35);
    step();
    const hyps = $$('.hyp', el), verd = $$('.verdict', el);
    tl.fromTo(hyps, { autoAlpha: 0, y: 50 }, { autoAlpha: 1, y: 0, duration: .6, stagger: .12, ease: 'power3.out' });
    tl.set(verd, { autoAlpha: 0 }, 0);
    step();
    tl.fromTo(verd, { autoAlpha: 0, scale: 2.4, rotation: -14 }, { autoAlpha: 1, scale: 1, rotation: 4, duration: .45, stagger: .22, ease: 'back.out(2.2)' });
    tl.to(hyps[1], { borderColor: 'rgba(236,100,97,.45)', duration: .3 }, '<.25');
    tl.to([hyps[0], hyps[2]], { borderColor: 'rgba(125,203,110,.45)', duration: .3 }, '<');
    step();
  };

  /* ---------- 4 · data ---------- */
  SL.data = (el, tl, step) => {
    header(tl, el);
    const row = (id, at) => {
      const r = $(id, el);
      tl.fromTo($('.barf', r), { scaleX: 0, transformOrigin: '0% 50%' }, { scaleX: 1, duration: .8, ease: 'power3.out' }, at);
      tl.fromTo([$('.v', r), $('.t', r)], { autoAlpha: 0, x: -20 }, { autoAlpha: 1, x: 0, duration: .5, stagger: .1 }, '<.15');
      countUp(tl, $('.v', r), $('.v', r).dataset.to, '<', { d: 1.1 });
    };
    row('#f1', .3); row('#f2', '+=.1');
    tl.fromTo('#al1', { autoAlpha: 0, x: 40 }, { autoAlpha: 1, x: 0, duration: .5, ease: 'back.out(1.6)' }, '+=.1');
    step();
    row('#f3', '+=0');
    tl.fromTo('#al2', { autoAlpha: 0, x: 40 }, { autoAlpha: 1, x: 0, duration: .5, ease: 'back.out(1.6)' }, '+=.05');
    row('#f4', '+=.1');
    step();
    const c = chart('c-valid', { l: 64, r: 16, t: 50, b: 44 });
    const pm = new Map(KC.monthly.map((d) => [d.ym, d.p]));
    const pts = KC.lasalgaon.map((d) => ({ t: d3.timeParse('%Y-%m')(d.ym), las: d.p, mh: pm.get(d.ym) })).filter((d) => d.t && d.las != null && d.mh != null);
    const x = d3.scaleTime(d3.extent(pts, (d) => d.t), [0, c.w]);
    const y = d3.scaleLinear([0, d3.max(pts, (d) => Math.max(d.las, d.mh)) * 1.05], [c.h, 0]).nice();
    yAxis(c, y, (d) => '₹' + d, 4);
    xAxis(c, x, d3.timeFormat('%Y')).call((a) => a.selectAll('text').style('font-size', '18px'));
    const cl = clip(c);
    const lineF = (k) => d3.line().x((d) => x(d.t)).y((d) => y(d[k])).curve(d3.curveMonotoneX)(pts);
    const g = c.g.append('g').attr('clip-path', cl.url);
    g.append('path').attr('d', lineF('las')).attr('fill', 'none').attr('stroke', C.sky).attr('stroke-width', 3.5);
    g.append('path').attr('d', lineF('mh')).attr('fill', 'none').attr('stroke', C.gold).attr('stroke-width', 3);
    const lg = c.svg.append('g').attr('transform', 'translate(64,18)');
    lg.append('text').attr('class', 'lbl-s').attr('fill', C.gold).text('— Our Maharashtra price');
    lg.append('text').attr('class', 'lbl-s').attr('x', 270).attr('fill', C.sky).text('— NHRDF Lasalgaon');
    axisTitle(c, '₹/kg', -60, -28);
    fadeUp(tl, [c.svg.selectAll('.axis').nodes(), lg.node()].flat(), '+=0', { st: .03 });
    reveal(tl, cl, '<.2', 1.6);
    fadeUp(tl, '#val-card', '-=.4');
    step();
  };

  /* ---------- 5 · 3D price landscape ---------- */
  SL.landscape = (el, tl, step) => {
    header(tl, el);
    const g = GL('gl-land', 34), { scene, camera } = g;
    scene.add(new THREE.AmbientLight(0xffffff, .55));
    const dl = new THREE.DirectionalLight(0xfff0dd, .9); dl.position.set(6, 14, 10); scene.add(dl);
    const dl2 = new THREE.DirectionalLight(0xff8fc8, .45); dl2.position.set(-10, 6, -8); scene.add(dl2);
    const years = [...new Set(KC.monthly.map((d) => d.y))];
    const pmax = d3.max(KC.monthly, (d) => d.p), H = 6.2;
    const col = d3.scaleSequential([2, pmax * .8], d3.interpolateRgbBasis(['#4A1838', '#8E2F5E', '#C2508D', '#E2834F', '#EDB94E', '#FFE9A8']));
    const box = new THREE.BoxGeometry(.82, 1, .82); box.translate(0, .5, 0);
    const bars = [], X = (m) => (m - 6.5) * 1.05, Z = (y) => (y - 2019) * 1.12;
    const grp = new THREE.Group(); scene.add(grp);
    KC.monthly.forEach((d) => {
      const c3 = new THREE.Color(col(d.p));
      const mat = new THREE.MeshStandardMaterial({ color: c3, roughness: .45, metalness: .08, emissive: c3.clone(), emissiveIntensity: .12, transparent: true });
      const m = new THREE.Mesh(box, mat);
      m.position.set(X(d.m), 0, Z(d.y)); m.userData = { d, h: Math.max(.05, d.p / pmax * H), base: c3 };
      m.scale.set(1, .0001, 1); grp.add(m); bars.push(m);
    });
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(15.5, 14.5), new THREE.MeshBasicMaterial({ color: 0x2a1823, transparent: true, opacity: .55 }));
    plane.rotation.x = -Math.PI / 2; plane.position.y = -.01; grp.add(plane);
    const grid = new THREE.GridHelper(15, 15, 0x4b3443, 0x33222d); grid.position.y = 0; grp.add(grid);
    const labs = [];
    MON.forEach((m, i) => { const s = label(m, { size: 54, h: .42, color: '#D8C7D2' }); s.position.set(X(i + 1), .05, Z(2024) + 1.1); grp.add(s); labs.push(s); });
    years.forEach((y) => { const s = label(String(y), { size: 54, h: .4, color: '#B9A8B3' }); s.position.set(X(1) - 1.35, .05, Z(y)); grp.add(s); labs.push(s); });
    const find = (ym) => bars.find((b) => b.userData.d.ym === ym);
    const hi = find(KC.eda.pmax_m), lo = find(KC.eda.pmin_m);
    const sHi = label(`₹${KC.eda.pmax.toFixed(1)}/kg · ${mname(KC.eda.pmax_m)}`, { size: 52, h: .55, color: '#1D1420', bg: '#EC6461', depthTest: false });
    const sLo = label(`₹${KC.eda.pmin.toFixed(1)}/kg · ${mname(KC.eda.pmin_m)}`, { size: 52, h: .55, color: '#1D1420', bg: '#6FBCDD', depthTest: false });
    sHi.position.set(hi.position.x, hi.userData.h + .7, hi.position.z); sLo.position.set(lo.position.x, lo.userData.h + .8, lo.position.z);
    sHi.renderOrder = sLo.renderOrder = 10; grp.add(sHi, sLo);
    const sApr = label('April: harvest low', { size: 50, h: .5, color: '#1D1420', bg: '#EC6461', depthTest: false });
    const sNov = label('Oct–Dec: peak', { size: 50, h: .5, color: '#1D1420', bg: '#EDB94E', depthTest: false });
    sApr.position.set(X(4), 3.1, Z(2024) + 1.2); sNov.position.set(X(11), 5.2, Z(2024) + 1.2);
    sApr.renderOrder = sNov.renderOrder = 10; grp.add(sApr, sNov);

    const st = { grow: 0, az: -.95, el: .62, dist: 25, ty: 1.2, hl: 0, spike: 0, lab: 0 };
    const tgt = new THREE.Vector3();
    g.update = (t) => {
      const az = st.az + Math.sin(t * .15) * .04;
      tgt.set(0, st.ty, .3);
      camera.position.set(tgt.x + st.dist * Math.cos(st.el) * Math.sin(az), tgt.y + st.dist * Math.sin(st.el), tgt.z + st.dist * Math.cos(st.el) * Math.cos(az));
      camera.lookAt(tgt);
      bars.forEach((b) => {
        const d = b.userData.d, delay = ((d.m - 1) / 11) * .55 + ((d.y - 2014) / 10) * .25;
        b.scale.y = Math.max(.0001, easeOut(clamp01((st.grow - delay) / .4)) * b.userData.h);
        const keyHL = d.m === 4 || d.m >= 10, keySP = d.ym === KC.eda.pmax_m || d.ym === KC.eda.pmin_m || d.y === 2019;
        let op = 1 - .78 * st.hl * (keyHL ? 0 : 1);
        op = op * (1 - .8 * st.spike * (keySP ? 0 : 1)) + (keySP ? .0 : 0);
        b.material.opacity = Math.max(.12, op);
        b.material.emissiveIntensity = .12 + .45 * (st.hl * (keyHL ? 1 : 0) + st.spike * (keySP ? 1 : 0));
      });
      labs.forEach((s) => { s.material.opacity = st.lab; });
      sApr.material.opacity = sNov.material.opacity = st.hl * (1 - st.spike);
      sHi.material.opacity = sLo.material.opacity = st.spike;
    };
    tl.to(st, { lab: 1, duration: .6 }, .3)
      .to(st, { grow: 1.2, duration: 2.6, ease: 'none' }, .3)
      .to(st, { az: -.62, el: .55, dist: 22.5, duration: 3, ease: 'power2.out' }, 0);
    fadeUp(tl, '#ld1', .8);
    step();
    tl.to(st, { az: 0, el: .24, dist: 21, ty: 1.8, duration: 1.6, ease: 'power2.inOut' })
      .to(st, { hl: 1, duration: .8 }, '-=.6');
    fadeOut(tl, '#ld1', '<'); fadeUp(tl, '#ld2', '<.2');
    step();
    tl.to(st, { az: .75, el: .5, dist: 22, ty: 1.4, duration: 1.6, ease: 'power2.inOut' })
      .to(st, { hl: 0, spike: 1, duration: .8 }, '-=.7');
    fadeOut(tl, '#ld2', '<'); fadeUp(tl, '#ld3', '<.2');
    step();
  };

  /* ---------- 6 · seasonality + H1 ---------- */
  SL.h1 = (el, tl, step) => {
    header(tl, el);
    const c = chart('c-h1', { l: 70, r: 30, t: 40, b: 50 });
    const x = d3.scalePoint(MON, [0, c.w]).padding(.4), y = d3.scaleLinear([.4, 1.7], [c.h, 0]);
    yAxis(c, y, (d) => d.toFixed(1) + '×', 5); xAxis(c, x, (d) => d);
    c.g.append('line').attr('x1', 0).attr('x2', c.w).attr('y1', y(1)).attr('y2', y(1)).attr('stroke', 'rgba(255,255,255,.4)').attr('stroke-dasharray', '6 8');
    const mk = (k, color, cl) => {
      const g = c.g.append('g').attr('clip-path', cl.url);
      g.append('path').attr('d', d3.line().x((d) => x(d.m)).y((d) => y(d[k])).curve(d3.curveCatmullRom)(KC.season))
        .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 5).attr('stroke-linecap', 'round');
      g.selectAll('circle').data(KC.season).join('circle').attr('cx', (d) => x(d.m)).attr('cy', (d) => y(d[k])).attr('r', 7)
        .attr('fill', '#120B10').attr('stroke', color).attr('stroke-width', 3);
      return g;
    };
    const c1 = clip(c), c2 = clip(c);
    mk('a', C.copper, c1); mk('p', C.gold, c2);
    const ann = (txt, xm, yv, color, anchor = 'middle') => c.g.append('text').attr('class', 'lbl').attr('x', x(xm)).attr('y', y(yv))
      .attr('text-anchor', anchor).attr('fill', color).text(txt);
    const a1 = ann('harvest arrivals pile up', 'Mar', 1.5, C.copper), a2 = ann('price lowest', 'Apr', .44, C.gold), a3 = ann('price peaks as stocks run down', 'Oct', 1.66, C.gold);
    fadeUp(tl, c.svg.selectAll('.axis').nodes(), .2, { st: .03 });
    fadeUp(tl, legend(el), .3);
    reveal(tl, c1, .5, 1.6); fadeUp(tl, a1.node(), 1.4);
    step();
    reveal(tl, c2, '+=0', 1.6); fadeUp(tl, [a2.node(), a3.node()], '-=.6', { st: .2 });
    step();
    fadeUp(tl, '#h1-card', '+=0');
    tl.fromTo('#h1-card .num-big', { scale: .7, transformOrigin: '0% 50%' }, { scale: 1, duration: .6, ease: 'back.out(2)' }, '<.2');
    fadeUp(tl, '#h1-why', '<.35');
    step();
  };

  /* ---------- 7 · ten models ---------- */
  SL.models = (el, tl, step) => {
    header(tl, el);
    const SHORT = { naive: 'Naive (last month)', seasonal_naive: 'Seasonal naive', moving_average_12: '12-month moving average',
      seasonal_moving_average: 'Seasonal index × MA', seasonal_ses: 'Seasonal index × exp. smoothing', holt_winters: 'Holt–Winters',
      regression_trend_season: 'Regression: trend + month', regression_level_season: 'Regression: level + month',
      seasonal_moving_average_long: '28-yr seasonal index × MA', seasonal_ses_long: '28-yr seasonal × exp. smoothing' };
    const data = [...KC.forecast.methods].sort((a, b) => a.val_mape - b.val_mape);
    const c = chart('c-models', { l: 400, r: 70, t: 20, b: 70 });
    const y = d3.scaleBand(data.map((d) => d.key), [0, c.h]).padding(.28), x = d3.scaleLinear([0, 65], [0, c.w]);
    c.g.append('g').attr('class', 'axis grid').attr('transform', `translate(0,${c.h})`)
      .call(d3.axisBottom(x).ticks(6).tickSize(-c.h).tickFormat((d) => d + '%')).call((a) => a.select('.domain').remove()).call((a) => a.selectAll('text').attr('y', 16));
    axisTitle(c, 'ERROR ON VALIDATION SEASONS 2019–22 (MAPE)', 0, c.h + 62);
    const best = KC.forecast.best;
    c.g.selectAll('text.ml').data(data).join('text').attr('class', 'ml lbl-s').attr('x', -18).attr('y', (d) => y(d.key) + y.bandwidth() / 2 + 7)
      .attr('text-anchor', 'end').attr('fill', (d) => d.key === best ? C.gold : C.muted).style('font-weight', (d) => d.key === best ? 800 : 600).text((d) => SHORT[d.key]);
    const bars = c.g.selectAll('rect.b').data(data).join('rect').attr('class', 'b').attr('x', 0).attr('y', (d) => y(d.key))
      .attr('height', y.bandwidth()).attr('width', (d) => x(d.val_mape)).attr('rx', 8)
      .attr('fill', (d) => d.key === best ? C.gold : 'rgba(180,64,127,.55)');
    const vals = c.g.selectAll('text.v').data(data).join('text').attr('class', 'v lbl').attr('x', (d) => x(d.val_mape) + 12)
      .attr('y', (d) => y(d.key) + y.bandwidth() / 2 + 8).attr('fill', (d) => d.key === best ? C.gold : C.ink).text((d) => d.val_mape.toFixed(1) + '%');
    const dia = c.g.selectAll('path.t').data(data).join('path').attr('class', 't')
      .attr('d', d3.symbol(d3.symbolDiamond, 260)).attr('transform', (d) => `translate(${x(d.test_mape)},${y(d.key) + y.bandwidth() / 2})`)
      .attr('fill', C.pink).attr('stroke', '#120B10').attr('stroke-width', 2);
    // split timeline
    const sp = d3.select('#split').append('svg').attr('width', 480).attr('height', 120);
    const segs = [['Fit', '≤ 2018', 0, 170, 'rgba(255,255,255,.14)', C.muted], ['Validate', '2019–22', 176, 176, 'rgba(237,185,78,.25)', C.gold], ['Test 🔒', '2023–24', 358, 122, 'rgba(229,131,184,.22)', C.pink]];
    segs.forEach(([a, b, x0, w, f, tc]) => {
      sp.append('rect').attr('x', x0).attr('y', 10).attr('width', w).attr('height', 64).attr('rx', 12).attr('fill', f);
      sp.append('text').attr('x', x0 + w / 2).attr('y', 40).attr('text-anchor', 'middle').attr('fill', tc).style('font', '800 22px Manrope, sans-serif').text(a);
      sp.append('text').attr('x', x0 + w / 2).attr('y', 64).attr('text-anchor', 'middle').attr('fill', C.muted).style('font', '600 17px JetBrains Mono, monospace').text(b);
    });
    sp.append('text').attr('x', 0).attr('y', 108).attr('fill', C.dim).style('font', '600 17px Manrope, sans-serif').text('Pick the model on validation · judge it once on test');
    fadeUp(tl, c.svg.selectAll('.axis, .lbl-m').nodes(), .2, { st: .03 });
    fadeUp(tl, c.g.selectAll('text.ml').nodes(), .3, { st: .04, y: 0 });
    tl.fromTo(bars.nodes(), { scaleX: 0, transformOrigin: '0% 50%' }, { scaleX: 1, duration: .7, stagger: .06, ease: 'power3.out' }, .45);
    fadeUp(tl, vals.nodes(), 1.0, { st: .05, y: 0 });
    fadeUp(tl, '#m-split', .6);
    step();
    tl.fromTo(dia.nodes(), { autoAlpha: 0, scale: 0, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: .4, stagger: .05, ease: 'back.out(2.5)' })
      .to(bars.nodes(), { opacity: (i, t) => d3.select(t).datum().key === best ? 1 : .55, duration: .4 }, '<');
    fadeUp(tl, '#m-test', '<.3');
    step();
    const bb = bars.filter((d) => d.key === best).node();
    tl.fromTo(bb, { filter: 'drop-shadow(0 0 0 rgba(237,185,78,0))' }, { filter: 'drop-shadow(0 0 18px rgba(237,185,78,.9))', duration: .6 });
    fadeUp(tl, '#m-why', '<');
    step();
  };

  /* ---------- 8 · forecast vs actual ---------- */
  SL.ftest = (el, tl, step) => {
    header(tl, el);
    const best = KC.forecast.best;
    const all = [];
    ['2023', '2024'].forEach((yr) => { all.push(...KC.forecast.actual[yr], ...KC.forecast.paths[best][yr]); });
    const ymax = Math.ceil(d3.max(all) / 100 / 5) * 5;
    const panel = (yr) => {
      const c = chart('c-f' + yr.slice(2), { l: 70, r: 26, t: 64, b: 50 });
      const x = d3.scalePoint(SEASON, [0, c.w]).padding(.2), y = d3.scaleLinear([0, ymax], [c.h, 0]);
      yAxis(c, y, (d) => '₹' + d, 5); xAxis(c, x, (d) => d);
      c.svg.append('text').attr('x', c.m.l).attr('y', 34).attr('fill', C.ink).style('font', '800 38px Bricolage Grotesque, sans-serif').text(yr);
      c.svg.append('text').attr('x', c.m.l + 110).attr('y', 34).attr('class', 'lbl-m').text('₹/KG · UNSEEN SEASON');
      const act = KC.forecast.actual[yr].map((v) => v / 100), fc = KC.forecast.paths[best][yr].map((v) => v / 100);
      const cl = clip(c), g = c.g.append('g').attr('clip-path', cl.url);
      const area = d3.area().x((d, i) => x(SEASON[i])).y0((d, i) => y(fc[i])).y1((d) => y(d)).curve(d3.curveMonotoneX);
      g.append('path').attr('d', area(act)).attr('fill', 'rgba(237,185,78,.10)');
      g.append('path').attr('d', d3.line().x((d, i) => x(SEASON[i])).y((d) => y(d)).curve(d3.curveMonotoneX)(fc))
        .attr('fill', 'none').attr('stroke', C.pink).attr('stroke-width', 4).attr('stroke-dasharray', '10 9');
      g.append('path').attr('d', d3.line().x((d, i) => x(SEASON[i])).y((d) => y(d)).curve(d3.curveMonotoneX)(act))
        .attr('fill', 'none').attr('stroke', C.gold).attr('stroke-width', 5);
      g.selectAll('circle').data(act).join('circle').attr('cx', (d, i) => x(SEASON[i])).attr('cy', (d) => y(d)).attr('r', 6.5).attr('fill', C.gold);
      return { c, cl };
    };
    const p23 = panel('2023'), p24 = panel('2024');
    fadeUp(tl, p23.c.svg.selectAll('.axis, text').nodes(), .2, { st: .01, y: 0 });
    fadeUp(tl, legend(el), .3);
    reveal(tl, p23.cl, .5, 1.8);
    step();
    fadeUp(tl, p24.c.svg.selectAll('.axis, text').nodes(), '+=0', { st: .01, y: 0 });
    reveal(tl, p24.cl, '<.2', 1.8);
    step();
    fadeUp(tl, $$('#f-metrics .card'), '+=0', { st: .12 });
    step();
  };

  /* ---------- 9 · LP ---------- */
  SL.lp = (el, tl, step) => {
    header(tl, el);
    const s = d3.select('#c-flow').append('svg').attr('width', 820).attr('height', 640).attr('viewBox', '0 0 820 640');
    const defs = s.append('defs');
    defs.append('marker').attr('id', 'arr').attr('viewBox', '0 0 10 10').attr('refX', 8).attr('refY', 5).attr('markerWidth', 7).attr('markerHeight', 7)
      .attr('orient', 'auto-start-reverse').append('path').attr('d', 'M0,0L10,5L0,10z').attr('fill', '#D9C7D2');
    const grad = defs.append('linearGradient').attr('id', 'tankg').attr('x1', 0).attr('y1', 1).attr('x2', 0).attr('y2', 0);
    grad.append('stop').attr('offset', 0).attr('stop-color', '#5f9e55'); grad.append('stop').attr('offset', 1).attr('stop-color', '#7DCB6E');
    const T = (x, y, t, cls = 'lbl', a = 'middle', fill) => s.append('text').attr('class', cls).attr('x', x).attr('y', y).attr('text-anchor', a).attr('fill', fill || null).text(t);
    const parts = [];
    // harvest
    const hv = s.append('g');
    hv.append('circle').attr('cx', 120).attr('cy', 120).attr('r', 92).attr('fill', 'rgba(237,185,78,.12)').attr('stroke', C.gold).attr('stroke-width', 3);
    hv.append('text').attr('x', 120).attr('y', 118).attr('text-anchor', 'middle').attr('fill', C.gold).style('font', '800 46px Bricolage Grotesque, sans-serif').text(n(KC.lp.Q));
    hv.append('text').attr('x', 120).attr('y', 152).attr('text-anchor', 'middle').attr('class', 'lbl-s').text('t at harvest');
    parts.push(hv.node());
    // april sale
    const ap = s.append('g');
    ap.append('rect').attr('x', 20).attr('y', 430).attr('width', 200).attr('height', 130).attr('rx', 22).attr('fill', 'rgba(255,255,255,.05)').attr('stroke', 'rgba(255,255,255,.25)');
    ap.append('text').attr('x', 120).attr('y', 476).attr('text-anchor', 'middle').attr('class', 'lbl').text('Sell in April');
    ap.append('text').attr('x', 120).attr('y', 512).attr('text-anchor', 'middle').attr('class', 'lbl').attr('fill', C.gold).text(`≥ ${KC.lp.L} t`);
    ap.append('text').attr('x', 120).attr('y', 542).attr('text-anchor', 'middle').attr('class', 'lbl-s').text('repays crop loans');
    // tank
    const tk = s.append('g');
    tk.append('rect').attr('x', 400).attr('y', 30).attr('width', 260).attr('height', 260).attr('rx', 26).attr('fill', 'rgba(255,255,255,.04)').attr('stroke', 'rgba(255,255,255,.3)').attr('stroke-width', 2);
    const fill = tk.append('rect').attr('x', 404).attr('y', 30 + 260 * .3).attr('width', 252).attr('height', 260 * .7 - 4).attr('rx', 22).attr('fill', 'url(#tankg)').attr('opacity', .85).node();
    tk.append('text').attr('x', 530).attr('y', 74).attr('text-anchor', 'middle').attr('class', 'lbl').text('Store');
    tk.append('text').attr('x', 530).attr('y', 190).attr('text-anchor', 'middle').attr('fill', '#10200d').style('font', '800 40px Bricolage Grotesque, sans-serif').text(`≤ ${KC.lp.C} t`);
    // rot drips
    const drips = s.append('g');
    [470, 530, 590].forEach((x, i) => drips.append('path').attr('d', `M${x},300 q-9,16 0,26 q9,-10 0,-26z`).attr('fill', C.red).attr('class', 'drip').attr('data-i', i));
    T(530, 360, 'rot: δ lost per month', 'lbl-s', 'middle', C.red);
    // monthly sales
    const ms = s.append('g');
    SEASON.slice(1).forEach((m, i) => {
      const x = 300 + i * 64;
      ms.append('rect').attr('x', x).attr('y', 470).attr('width', 54).attr('height', 54).attr('rx', 12).attr('fill', 'rgba(125,203,110,.14)').attr('stroke', 'rgba(125,203,110,.55)');
      ms.append('text').attr('x', x + 27).attr('y', 504).attr('text-anchor', 'middle').attr('class', 'lbl-s').style('font-size', '17px').text(m);
    });
    T(553, 568, `sell ≤ ${KC.lp.U} t a month · store empty by December`, 'lbl-s');
    // arrows
    const A = (d) => s.append('path').attr('d', d).attr('fill', 'none').attr('stroke', '#D9C7D2').attr('stroke-width', 3).attr('marker-end', 'url(#arr)').node();
    const arrs = [A('M120,214 L120,420'), A('M214,120 L392,120'), A('M530,380 C530,420 540,440 553,462')];
    const lblA = T(306, 104, 'store the rest', 'lbl-s');
    // animation
    tl.fromTo(hv.node(), { autoAlpha: 0, scale: .5, transformOrigin: '120px 120px' }, { autoAlpha: 1, scale: 1, duration: .6, ease: 'back.out(2)' }, .3);
    arrs.forEach((a, i) => { const L = a.getTotalLength(); tl.fromTo(a, { strokeDasharray: L, strokeDashoffset: L }, { strokeDashoffset: 0, duration: .5, ease: 'power2.out' }, .8 + [0, .2, 1.3][i]); });
    fadeUp(tl, ap.node(), 1.1); fadeUp(tl, [tk.node(), lblA.node()], 1.0);
    tl.fromTo(fill, { attr: { y: 290, height: 0 } }, { attr: { y: 30 + 260 * .3, height: 260 * .7 - 4 }, duration: 1, ease: 'power2.out' }, 1.3);
    fadeUp(tl, [drips.node(), ...s.selectAll('text.lbl-s').nodes().slice(-2), ms.node()], 1.9, { st: .1 });
    step();
    fadeUp(tl, '#eq1', '+=0'); step();
    fadeUp(tl, '#eq2 .kicker', '+=0');
    fadeUp(tl, $$('#eq2 .cons > *'), '<.1', { st: .06, y: 14 });
    step();
    fadeUp(tl, '#eq3', '+=0');
    tl.fromTo($$('#eq3 tr'), { autoAlpha: 0, x: 20 }, { autoAlpha: 1, x: 0, stagger: .12, duration: .4 }, '<.2');
    step();
    // ambient drip (pure decoration)
    gsap.to($$('.drip', s.node()), { y: 22, opacity: 0, duration: 1.4, repeat: -1, stagger: .45, ease: 'power1.in' });
  };

  /* ---------- 10 · 2024 plan ---------- */
  SL.plan = (el, tl, step) => {
    header(tl, el);
    const c = chart('c-plan', { l: 80, r: 90, t: 40, b: 56 });
    const x = d3.scaleBand(SEASON, [0, c.w]).padding(.3), y = d3.scaleLinear([0, 1050], [c.h, 0]);
    const fc = KC.plan.forecast.map((v) => v / 1000), yP = d3.scaleLinear([0, Math.ceil(d3.max(fc) / 5) * 5], [c.h, 0]);
    yAxis(c, y, (d) => n(d), 5); xAxis(c, x, (d) => d);
    const ra = c.g.append('g').attr('class', 'axis').attr('transform', `translate(${c.w},0)`).call(d3.axisRight(yP).ticks(5).tickSize(0).tickPadding(14).tickFormat((d) => '₹' + d))
      .call((a) => a.select('.domain').remove());
    axisTitle(c, 'TONNES', -76, -16); const rt = axisTitle(c, '₹/KG', c.w + 86, -16, 'end');
    const cx = (i) => x(SEASON[i]) + x.bandwidth() / 2;
    const P = KC.plan.C;
    const clS = clip(c), clP = clip(c);
    const stock = c.g.append('path').attr('clip-path', clS.url)
      .attr('d', d3.area().x((d) => d[0]).y0(c.h).y1((d) => y(d[1])).curve(d3.curveStepAfter)(
        P.s.map((v, i) => [x(SEASON[i]), v]).concat([[x(SEASON[8]) + x.bandwidth(), P.s[8]]])))
      .attr('fill', 'rgba(125,203,110,.16)').attr('stroke', 'rgba(125,203,110,.6)').attr('stroke-width', 2);
    const price = c.g.append('path').attr('clip-path', clP.url)
      .attr('d', d3.line().x((d, i) => cx(i)).y((d) => yP(d)).curve(d3.curveMonotoneX)(fc))
      .attr('fill', 'none').attr('stroke', C.pink).attr('stroke-width', 4).attr('stroke-dasharray', '10 9');
    const bars = c.g.selectAll('rect.s').data(P.x).join('rect').attr('class', 's').attr('x', (d, i) => x(SEASON[i])).attr('width', x.bandwidth())
      .attr('y', (d) => y(d)).attr('height', (d) => c.h - y(d)).attr('rx', 7).attr('fill', C.green);
    const bl = c.g.selectAll('text.sv').data(P.x).join('text').attr('class', 'sv lbl').attr('text-anchor', 'middle')
      .attr('x', (d, i) => cx(i)).attr('y', (d) => y(d) - 14).attr('fill', C.green).text((d) => d > 0.5 ? n(d) : '');
    const ghost = c.g.append('rect').attr('x', x('Apr') - 6).attr('width', x.bandwidth() + 12).attr('y', y(1000)).attr('height', c.h - y(1000))
      .attr('rx', 9).attr('fill', 'rgba(226,131,79,.12)').attr('stroke', C.copper).attr('stroke-width', 3).attr('stroke-dasharray', '8 6');
    const gl = c.g.append('text').attr('class', 'lbl').attr('x', x('Apr') + x.bandwidth() + 18).attr('y', y(1000) + 30).attr('fill', C.copper).text('Chawl: sell all 1,000 t in April');
    fadeUp(tl, [...c.svg.selectAll('.axis').nodes(), rt.node()], .2, { st: .03 });
    fadeUp(tl, legend(el), .3);
    reveal(tl, clP, .5, 1.5);
    step();
    reveal(tl, clS, '+=0', 1.4, 'none');
    tl.fromTo(bars.nodes(), { scaleY: 0, transformOrigin: '50% 100%' }, { scaleY: 1, duration: .5, stagger: .12, ease: 'back.out(1.6)' }, '<.1');
    fadeUp(tl, bl.nodes(), '<.5', { st: .1, y: 10 });
    fadeUp(tl, '#pl1', '<.2');
    step();
    tl.fromTo(ghost.node(), { scaleY: 0, autoAlpha: 0, transformOrigin: '50% 100%' }, { scaleY: 1, autoAlpha: 1, duration: .7, ease: 'power3.out' });
    fadeUp(tl, gl.node(), '<.4', { y: 0 });
    fadeUp(tl, '#pl2', '<');
    step();
    fadeUp(tl, '#pl3', '+=0');
    step();
  };

  /* ---------- 11 · backtest ---------- */
  SL.backtest = (el, tl, step) => {
    header(tl, el);
    const B = KC.backtest, yrs = B.years.map(String);
    const c = chart('c-bt', { l: 96, r: 30, t: 40, b: 56 });
    const x = d3.scaleBand(yrs, [0, c.w]).padding(.3), y = d3.scaleLinear([-2000, 12000], [c.h, 0]);
    yAxis(c, y, (d) => (d > 0 ? '+' : '') + n(d), 7); xAxis(c, x, (d) => d);
    axisTitle(c, '₹ PER TONNE VS SELLING ALL AT HARVEST', -90, -16);
    c.g.append('line').attr('x1', 0).attr('x2', c.w).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'rgba(255,255,255,.5)');
    const bars = c.g.selectAll('rect.b').data(B.C).join('rect').attr('class', 'b')
      .attr('x', (d, i) => x(yrs[i])).attr('width', x.bandwidth()).attr('y', (d) => y(Math.max(0, d))).attr('height', (d) => Math.abs(y(d) - y(0)))
      .attr('rx', 7).attr('fill', (d) => d >= 0 ? C.green : C.red).attr('data-neg', (d) => d < 0 ? 1 : null);
    const vl = c.g.selectAll('text.v').data(B.C).join('text').attr('class', 'v lbl-s').attr('text-anchor', 'middle')
      .attr('x', (d, i) => x(yrs[i]) + x.bandwidth() / 2).attr('y', (d) => d >= 0 ? y(d) - 12 : y(d) + 28)
      .attr('fill', (d) => d >= 0 ? C.green : C.red).style('font-weight', 800).text((d) => (d > 0 ? '+' : '') + n(d));
    const bdots = c.g.selectAll('rect.bd').data(B.B).join('rect').attr('class', 'bd').attr('x', (d, i) => x(yrs[i]) + 6).attr('width', x.bandwidth() - 12)
      .attr('y', (d) => y(d) - 3).attr('height', 6).attr('rx', 3).attr('fill', C.copper);
    const mean = B.test.mean_diff_rs_per_t;
    const ml = c.g.append('line').attr('x1', 0).attr('x2', c.w).attr('y1', y(mean)).attr('y2', y(mean)).attr('stroke', C.gold).attr('stroke-width', 3).attr('stroke-dasharray', '10 8');
    const mt = c.g.append('text').attr('class', 'lbl').attr('x', 8).attr('y', y(mean) - 14).attr('text-anchor', 'start').attr('fill', C.gold).text(`mean +₹${n(mean)}/t`);
    fadeUp(tl, c.svg.selectAll('.axis, .lbl-m').nodes(), .2, { st: .03 });
    fadeUp(tl, legend(el), .3);
    tl.fromTo(bars.nodes(), { scaleY: 0, transformOrigin: (i, t) => t.dataset.neg ? '50% 0%' : '50% 100%' }, { scaleY: 1, duration: .6, stagger: .12, ease: 'back.out(1.5)' }, .4);
    fadeUp(tl, vl.nodes(), .9, { st: .12, y: 10 });
    fadeUp(tl, bdots.nodes(), 1.2, { st: .05, y: 0 });
    fadeUp(tl, '#bt1', .5);
    step();
    tl.fromTo(ml.node(), { attr: { x2: 0 } }, { attr: { x2: c.w }, duration: .8, ease: 'power2.out' });
    fadeUp(tl, mt.node(), '<.5', { y: 0 });
    fadeUp(tl, '#bt2', '<');
    countUp(tl, $('#bt2 .num-big span'), mean, '<.1', { d: 1.2 });
    step();
    fadeUp(tl, '#bt3', '+=0');
    step();
  };

  /* ---------- 12 · all-India 3D ---------- */
  SL.india = (el, tl, step) => {
    header(tl, el);
    const g = GL('gl-india', 30), { scene, camera } = g;
    scene.add(new THREE.AmbientLight(0xffffff, .6));
    const dl = new THREE.DirectionalLight(0xffffff, .8); dl.position.set(5, 12, 8); scene.add(dl);
    const LON0 = 80.5, LAT0 = 22.5, X = (lon) => (lon - LON0) * .34, Z = (lat) => -(lat - LAT0) * .37;
    // cloud of all markets
    const cp = new Float32Array(KC.ai.cloud.length * 3);
    KC.ai.cloud.forEach(([lat, lon], i) => cp.set([X(lon), 0, Z(lat)], i * 3));
    const cg = new THREE.BufferGeometry(); cg.setAttribute('position', new THREE.BufferAttribute(cp, 3));
    const cloud = new THREE.Points(cg, new THREE.PointsMaterial({ size: .34, map: dotTexture(), color: 0xe2b8d2, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    scene.add(cloud);
    const base = new THREE.Mesh(new THREE.CircleGeometry(9.5, 64), new THREE.MeshBasicMaterial({ color: 0x24141e, transparent: true, opacity: .0 }));
    base.rotation.x = -Math.PI / 2; base.position.y = -.02; scene.add(base);
    const ring = new THREE.Mesh(new THREE.RingGeometry(9.4, 9.5, 96), new THREE.MeshBasicMaterial({ color: 0x5b3a4f, transparent: true, opacity: 0, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2; scene.add(ring);
    // columns for scored markets
    const gmax = d3.max(KC.ai.mk, (d) => Math.abs(d.g));
    const cyl = new THREE.CylinderGeometry(.085, .085, 1, 14); cyl.translate(0, .5, 0);
    const matW = new THREE.MeshStandardMaterial({ color: 0x7DCB6E, emissive: 0x2f6a27, emissiveIntensity: .5, roughness: .4 });
    const matL = new THREE.MeshStandardMaterial({ color: 0xEC6461, emissive: 0x7a2423, emissiveIntensity: .6, roughness: .4 });
    const cols = KC.ai.mk.map((d) => {
      const m = new THREE.Mesh(cyl, d.g >= 0 ? matW : matL);
      m.position.set(X(d.lon), 0, Z(d.lat));
      m.userData = { h: .2 + Math.sqrt(Math.abs(d.g) / gmax) * 2.6, delay: (d.lon - 68) / 30 * .6 };
      m.scale.set(1, .0001, 1); scene.add(m); return m;
    });
    const caps = new THREE.Points(new THREE.BufferGeometry().setFromPoints(cols.map((m) => m.position.clone())),
      new THREE.PointsMaterial({ size: .45, map: dotTexture(), color: 0xd6ffcc, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    scene.add(caps);
    // state labels
    const byState = d3.rollups(KC.ai.mk, (v) => ({ lat: d3.mean(v, (d) => d.lat), lon: d3.mean(v, (d) => d.lon) }), (d) => d.s);
    const tab = new Map(KC.ai.states_tab.map((s) => [s.s, s]));
    const pick = ['Maharashtra', 'Kerala', 'Punjab', 'Gujarat', 'Karnataka', 'Uttar Pradesh', 'West Bengal', 'Rajasthan'];
    const slabs = byState.filter(([s]) => pick.includes(s)).map(([s, p]) => {
      const t = tab.get(s), sp = label(`${s} ${t.w}/${t.n}`, { size: 46, h: .42, color: '#1D1420', bg: 'rgba(247,239,244,.92)', depthTest: false });
      sp.position.set(X(p.lon), 0, Z(p.lat)); sp.userData = { y: 4.9 }; sp.renderOrder = 10; scene.add(sp); return sp;
    });
    const st = { cloud: 0, grow: 0, az: -.15, el: 1.1, dist: 27, lab: 0 };
    const tgt = new THREE.Vector3(0, 0, .3);
    g.update = (t) => {
      const az = st.az + Math.sin(t * .12) * .05;
      camera.position.set(st.dist * Math.cos(st.el) * Math.sin(az), st.dist * Math.sin(st.el), .3 + st.dist * Math.cos(st.el) * Math.cos(az));
      camera.lookAt(tgt);
      cloud.material.opacity = st.cloud * .95; ring.material.opacity = st.cloud * .8; base.material.opacity = st.cloud * .5;
      cols.forEach((m) => { m.scale.y = Math.max(.0001, easeOutBack(clamp01((st.grow - m.userData.delay) / .45)) * m.userData.h); });
      caps.geometry.attributes.position.array.forEach((_, i, a) => { if (i % 3 === 1) a[i] = cols[(i - 1) / 3].scale.y; });
      caps.geometry.attributes.position.needsUpdate = true; caps.material.opacity = clamp01(st.grow - .9) * .9;
      slabs.forEach((s, i) => { s.material.opacity = clamp01(st.lab * 2 - i * .12); s.position.y = 2.6 + st.lab * .5; });
    };
    tl.to(st, { cloud: 1, duration: 1.2 }, .2).to(st, { dist: 23, el: 1.0, duration: 2.4, ease: 'power2.out' }, 0);
    fadeUp(tl, '#in1', .7);
    step();
    tl.to(st, { grow: 1.5, duration: 2.6, ease: 'none' })
      .to(st, { az: .25, el: .88, dist: 22, duration: 2.6, ease: 'power2.inOut' }, '<');
    step();
    tl.to(st, { lab: 1, duration: .9 });
    fadeOut(tl, '#in1', '<');
    fadeUp(tl, ['#in2', '#in3'], '<.2', { st: .2 });
    countUp(tl, $('#in2 .num-big > span'), KC.ai.wins, '<', { d: 1 });
    step();
  };

  /* ---------- 13 · value of loss rate ---------- */
  SL.value = (el, tl, step) => {
    header(tl, el);
    const c = chart('c-delta', { l: 96, r: 40, t: 40, b: 70 });
    const x = d3.scaleLinear([0, 27], [0, c.w]), y = d3.scaleLinear([-1000, 6000], [c.h, 0]);
    yAxis(c, y, (d) => (d > 0 ? '+' : '') + n(d), 7);
    c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.h})`).call(d3.axisBottom(x).ticks(9).tickSize(0).tickPadding(16).tickFormat((d) => d + '%'))
      .call((a) => a.select('.domain').attr('stroke', 'rgba(255,255,255,.2)'));
    axisTitle(c, 'STORAGE LOSS PER MONTH (δ)', 0, c.h + 64);
    axisTitle(c, 'MEAN GAIN ₹/T, 2017–24', -90, -26);
    c.g.append('line').attr('x1', 0).attr('x2', c.w).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'rgba(255,255,255,.5)');
    const toPts = (o) => Object.entries(o).map(([k, v]) => ({ d: +k * 100, g: v })).sort((a, b) => a.d - b.d);
    const cP = toPts(KC.sens.delta_C), bP = toPts(KC.sens.delta_B);
    const cl1 = clip(c), cl2 = clip(c);
    const draw = (pts, color, cl) => {
      const g = c.g.append('g').attr('clip-path', cl.url);
      g.append('path').attr('d', d3.line().x((d) => x(d.d)).y((d) => y(d.g)).curve(d3.curveMonotoneX)(pts)).attr('fill', 'none').attr('stroke', color).attr('stroke-width', 5);
      g.selectAll('circle').data(pts).join('circle').attr('cx', (d) => x(d.d)).attr('cy', (d) => y(d.g)).attr('r', 7).attr('fill', '#120B10').attr('stroke', color).attr('stroke-width', 3);
    };
    draw(cP, C.green, cl1); draw(bP, C.copper, cl2);
    const be = KC.sens.breakeven_B * 100;
    const beG = c.g.append('g');
    beG.append('line').attr('x1', x(be)).attr('x2', x(be)).attr('y1', y(5600)).attr('y2', c.h).attr('stroke', C.gold).attr('stroke-width', 2.5).attr('stroke-dasharray', '6 6');
    beG.append('text').attr('class', 'lbl').attr('x', x(be) + 12).attr('y', y(5400)).attr('fill', C.gold).text(`break-even ${be.toFixed(1)}%`);
    const mkG = c.g.append('g');
    const dB = KC.scen.B.delta * 100, dC = KC.scen.C.delta * 100;
    mkG.append('rect').attr('x', x(dB) - 1).attr('y', 0).attr('width', 2).attr('height', c.h).attr('fill', C.copper);
    mkG.append('text').attr('class', 'lbl').attr('x', x(dB) + 12).attr('y', y(1300)).attr('fill', C.copper).text(`chawl (ICAR) ${dB.toFixed(0)}%`);
    mkG.append('text').attr('class', 'lbl-s').attr('x', x(dB) + 12).attr('y', y(1300) + 28).text('→ never stores');
    const cy = y(d3.scaleLinear(cP.map((d) => d.d), cP.map((d) => d.g))(dC));
    mkG.append('circle').attr('cx', x(dC)).attr('cy', cy).attr('r', 15).attr('fill', 'none').attr('stroke', C.green).attr('stroke-width', 3);
    mkG.append('text').attr('class', 'lbl').attr('x', x(dC) + 26).attr('y', cy - 18).attr('fill', C.green).text(`cold / IoT ${dC.toFixed(1)}%`);
    fadeUp(tl, c.svg.selectAll('.axis, .lbl-m').nodes(), .2, { st: .03 });
    fadeUp(tl, legend(el), .3);
    reveal(tl, cl1, .5, 1.4); reveal(tl, cl2, .8, 1.4);
    fadeUp(tl, beG.node(), 1.9, { y: 0 });
    step();
    fadeUp(tl, $$('*', mkG.node()), '+=0', { st: .08, y: 0 });
    fadeUp(tl, '#v1', '<.2');
    countUp(tl, $('#v1 .num-big span'), KC.i40.uplift, '<');
    step();
    fadeUp(tl, ['#v2', '#v3'], '+=0', { st: .2 });
    step();
  };

  /* ---------- 14 · implications ---------- */
  SL.implications = (el, tl, step) => {
    header(tl, el);
    tl.fromTo($$('.imp', el), { autoAlpha: 0, y: 60, rotationX: -25, transformOrigin: '50% 0%' }, { autoAlpha: 1, y: 0, rotationX: 0, duration: .7, stagger: .15, ease: 'power3.out' }, .3);
    step();
    fadeUp(tl, $$('#lims .chip'), '+=0', { st: .09, y: 16 });
    step();
  };

  /* ---------- 15 · thanks ---------- */
  SL.thanks = (el, tl, step) => {
    const g = onionScene('gl-thanks');
    tl.fromTo(g.state, { open: 0 }, { open: 1, duration: 2, ease: 'none' }, 0)
      .fromTo(g.state, { cut: 0 }, { cut: 1, duration: 1.3, ease: 'power2.inOut' }, 1.1)
      .fromTo(g.state, { dust: 0 }, { dust: 1, duration: 1.4 }, .3);
    fadeUp(tl, $$('.logos > *', el), .1, { st: .1 });
    tl.fromTo($$('.logos .ring', el), { strokeDasharray: 300, strokeDashoffset: 300 }, { strokeDashoffset: 0, duration: 1, stagger: .07 }, .3);
    tl.fromTo($('h1', el), { autoAlpha: 0, y: 60 }, { autoAlpha: 1, y: 0, duration: .9, ease: 'power3.out' }, .5);
    fadeUp(tl, [$('.sub', el), ...$$('.mem', el), $('.links', el)], .9, { st: .06 });
    tl.fromTo('.qr', { autoAlpha: 0, scale: .8, rotation: -6 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: .7, ease: 'back.out(1.8)' }, 1.2);
    step();
  };
})();
