/* Kanda Code viva deck engine.
   Every slide owns one paused GSAP timeline with labels s0, s1, ... (one per click).
   Next plays the timeline forward to the next label; Back plays it in reverse to the previous one,
   so every animation runs exactly backwards. Changing slide reverses / replays the slide timelines too. */
(() => {
  const KC = window.KC, S = window.SLIDES;
  const stage = document.getElementById('stage');
  const slides = [...stage.querySelectorAll('.slide')];
  const N = slides.length;
  const SPK = ['#EDB94E', '#E2834F', '#E583B8', '#7DCB6E', '#6FBCDD'];
  const REV = 1.6;                  // reverse plays 1.6x faster, same path
  gsap.ticker.lagSmoothing(0);      // a slow projector laptop drops frames instead of slowing the animation
  const $ = (id) => document.getElementById(id);

  /* ---------- scale the 1920x1080 stage to the window ---------- */
  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `translate(-50%,-50%) scale(${s})`;
    window.STAGE_SCALE = s;
    (window.GLS || []).forEach((g) => g.resize());
  }
  addEventListener('resize', fit);
  fit();

  /* ---------- build every slide timeline ---------- */
  const tls = [], labels = [];
  slides.forEach((el) => {
    const tl = gsap.timeline({ paused: true });
    let k = 0;
    const step = (gap = 0) => tl.addLabel('s' + k++, '+=' + gap);
    (S[el.id] || ((e, t, st) => st()))(el, tl, step);
    if (!k) step();
    tl.pause(0, false);
    tls.push(tl);
    labels.push(Object.keys(tl.labels).sort((a, b) => tl.labels[a] - tl.labels[b]));
  });

  /* ---------- HUD ---------- */
  const segs = $('segs');
  for (let i = 0; i < N; i++) segs.appendChild(document.createElement('span'));
  const stepsEl = $('steps');
  function hud() {
    const el = slides[cur], sp = +el.dataset.speaker;
    stage.style.setProperty('--accent', SPK[sp]);
    $('spkname').textContent = KC.team[sp].name;
    $('sec').textContent = (el.dataset.section || '').toUpperCase();
    $('cnt').textContent = String(cur + 1).padStart(2, '0') + ' / ' + N;
    [...segs.children].forEach((s, i) => s.className = i < cur ? 'done' : i === cur ? 'cur' : '');
    $('foot').style.opacity = cur === 0 ? 0 : 1;
    const n = labels[cur].length;
    stepsEl.innerHTML = n > 1 ? labels[cur].map((_, i) => `<span class="${i <= stp ? 'on' : ''}"></span>`).join('') : '';
    gsap.to('#bar', { width: (1920 * (cur + (stp + 1) / n) / N) + 'px', duration: .5, ease: 'power2.out' });
    if (notesOn) showNotes();
    history.replaceState(null, '', '#' + (cur + 1) + (stp ? '.' + stp : ''));
  }

  /* ---------- navigation ---------- */
  let cur = 0, stp = 0, play = null, trans = null;
  function toStep(i, k) {
    const tl = tls[i], t = tl.labels[labels[i][k]];
    if (play) play.kill();
    const back = t < tl.time();
    const d = Math.abs(t - tl.time()) / (back ? REV : 1);
    play = tl.tweenTo(t, { duration: Math.max(d, 0.001), ease: 'none' });
  }
  function next() {
    if (stp < labels[cur].length - 1) { stp++; toStep(cur, stp); hud(); }
    else if (cur < N - 1) go(cur + 1, 1);
  }
  function prev() {
    if (stp > 0) { stp--; toStep(cur, stp); hud(); }
    else if (cur > 0) go(cur - 1, -1);
  }
  function go(j, dir, atStep) {
    if (j === cur || j < 0 || j >= N) return;
    const from = cur, outEl = slides[from], inEl = slides[j];
    if (play) play.kill();
    if (trans) trans.progress(1).kill();
    cur = j;
    const fromTl = tls[from];
    trans = gsap.timeline();
    if (dir > 0) {
      stp = atStep ?? 0;
      tls[j].pause(0, false);
      trans.to(outEl, { autoAlpha: 0, x: -90, scale: .985, filter: 'blur(6px)', duration: .55, ease: 'power2.in' }, 0)
           .fromTo(inEl, { autoAlpha: 0, x: 90, scale: 1.015, filter: 'blur(6px)' },
                   { autoAlpha: 1, x: 0, scale: 1, filter: 'blur(0px)', duration: .7, ease: 'power3.out' }, .35)
           .add(() => { fromTl.pause(fromTl.duration(), false); toStep(j, stp); }, .45);
    } else {
      stp = atStep ?? labels[j].length - 1;
      tls[j].pause(tls[j].labels[labels[j][stp]], false);
      const back = Math.min(.7, fromTl.time() / REV);
      play = fromTl.tweenTo(0, { duration: Math.max(back, .001), ease: 'none' });
      trans.to(outEl, { autoAlpha: 0, x: 90, scale: 1.015, filter: 'blur(6px)', duration: .5, ease: 'power2.in' }, Math.max(0, back - .3))
           .fromTo(inEl, { autoAlpha: 0, x: -90, scale: .985, filter: 'blur(6px)' },
                   { autoAlpha: 1, x: 0, scale: 1, filter: 'blur(0px)', duration: .7, ease: 'power3.out' }, Math.max(0, back - .05))
           .add(() => fromTl.pause(0, false));
    }
    hud();
  }
  function jump(j, k = 0) {
    j = Math.max(0, Math.min(N - 1, j));
    if (j === cur) { stp = Math.min(k, labels[j].length - 1); toStep(j, stp); hud(); return; }
    go(j, j > cur ? 1 : -1, Math.min(k, labels[j].length - 1));
  }

  /* ---------- start ---------- */
  function start() {
    const m = location.hash.match(/^#(\d+)(?:\.(\d+))?/);
    const j = m ? Math.max(0, Math.min(N - 1, +m[1] - 1)) : 0;
    const k = m && m[2] ? Math.min(+m[2], labels[j].length - 1) : 0;
    cur = j; stp = k;
    gsap.set(slides, { autoAlpha: 0 });
    gsap.set(slides[j], { autoAlpha: 1 });
    if (k > 0) { tls[j].pause(tls[j].labels[labels[j][k]], false); }
    else toStep(j, 0);
    hud();
  }

  /* ---------- input ---------- */
  const fs = () => document.fullscreenElement;
  function toggleFs() {
    if (fs()) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }
  document.addEventListener('fullscreenchange', () => { document.body.classList.toggle('fs', !!fs()); setTimeout(fit, 60); });
  let hintGone = false;
  const hideHint = () => { if (!hintGone) { hintGone = true; $('hint').classList.add('gone'); } };
  setTimeout(hideHint, 9000);

  document.addEventListener('click', (e) => {
    if (e.target.closest('a, #notes')) return;
    hideHint();
    if (!fs()) { toggleFs(); return; }
    if (e.clientX < innerWidth * .2) prev(); else next();
  });
  document.addEventListener('contextmenu', (e) => { e.preventDefault(); prev(); });
  let jumpBuf = '';
  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const k = e.key;
    if (/^\d$/.test(k)) { jumpBuf += k; $('jump').textContent = 'Go to ' + jumpBuf; $('jump').style.display = 'block'; return; }
    if (k === 'Enter' && jumpBuf) { jump(+jumpBuf - 1); jumpBuf = ''; $('jump').style.display = 'none'; e.preventDefault(); return; }
    if (jumpBuf && k === 'Escape') { jumpBuf = ''; $('jump').style.display = 'none'; return; }
    hideHint();
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(k)) { e.preventDefault(); next(); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace'].includes(k)) { e.preventDefault(); prev(); }
    else if (k === 'Home') jump(0);
    else if (k === 'End') jump(N - 1, 99);
    else if (k === 'f' || k === 'F') toggleFs();
    else if (k === 'n' || k === 'N') { notesOn = !notesOn; $('notes').classList.toggle('on', notesOn); if (notesOn) showNotes(); }
    else if (k === 't' || k === 'T') toggleTimer();
  });
  let tx = 0, ty = 0;
  document.addEventListener('touchstart', (e) => { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }, { passive: true });
  document.addEventListener('touchend', (e) => {
    const dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) { hideHint(); dx < 0 ? next() : prev(); }
  });
  let mouseT;
  document.addEventListener('mousemove', () => {
    document.body.classList.add('mouse'); clearTimeout(mouseT);
    mouseT = setTimeout(() => document.body.classList.remove('mouse'), 1800);
  });

  /* ---------- notes & timer ---------- */
  let notesOn = false;
  function showNotes() {
    const a = slides[cur].querySelector('aside.notes');
    $('notes').innerHTML = `<div class="who">Slide ${cur + 1} · ${KC.team[+slides[cur].dataset.speaker].name}</div>` + (a ? a.innerHTML : '');
  }
  let t0 = null, tick = null;
  function toggleTimer() {
    const el = $('timer');
    if (el.classList.toggle('on')) {
      if (t0 === null) t0 = Date.now();
      tick = setInterval(() => {
        const s = Math.floor((Date.now() - t0) / 1000);
        el.textContent = String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
        el.classList.toggle('warn', s >= 540 && s < 600); el.classList.toggle('over', s >= 600);
      }, 250);
    } else { clearInterval(tick); t0 = null; el.textContent = '00:00'; }
  }

  window.DECK = { next, prev, jump, state: () => ({ slide: cur, step: stp, steps: labels[cur].length, n: N }) };
  start();
})();
