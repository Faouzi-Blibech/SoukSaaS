// SoukSaaS agent network (ES module, inlined by dashboard/three_scene.py).
// three.js r160 is resolved through the importmap in the host page and loaded with dynamic import()
// so that a blocked CDN or missing WebGL falls back to the static SVG map instead of a blank frame.
const DATA = JSON.parse(document.getElementById("scene-data").textContent);
const ACCENT = 0x46b4ff;
const ALARM = 0xff5a36;
const VOID = 0x06080b;
const stage = document.getElementById("stage");
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let THREE = null;
const disposables = [];
const track = (o) => { disposables.push(o); return o; };

function showFallback(reason) {
  document.body.classList.add("nogl");
  const note = document.getElementById("fallback-note");
  if (note) note.textContent = reason;
}

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch (e) {
    return false;
  }
}

const maxAct = Math.max(1, ...Object.values(DATA.activity || {}));
const level = (k) => ((DATA.activity || {})[k] || 0) / maxAct;
const flaggedRecent = (k) => ((DATA.recent_flagged || {})[k] || 0);

function dotTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.35, "rgba(255,255,255,0.55)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return track(new THREE.CanvasTexture(c));
}

function circleLoop(radius, y, opacity) {
  const pts = [];
  for (let i = 0; i < 128; i++) {
    const a = (i / 128) * Math.PI * 2;
    pts.push(new THREE.Vector3(Math.cos(a) * radius, y, Math.sin(a) * radius));
  }
  const geo = track(new THREE.BufferGeometry().setFromPoints(pts));
  const mat = track(new THREE.LineBasicMaterial({ color: 0x2a3744, transparent: true, opacity }));
  return new THREE.LineLoop(geo, mat);
}

function buildBackdrop(scene) {
  [3.5, 6.5, 9.5].forEach((r, i) => scene.add(circleLoop(r, -4.4, 0.55 - i * 0.14)));
  const n = 260;
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const r = 16 + Math.random() * 18;
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[i * 3 + 1] = r * Math.cos(ph);
    pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
  }
  const geo = track(new THREE.BufferGeometry());
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const mat = track(new THREE.PointsMaterial({ color: 0x4b5866, size: 0.07, transparent: true, opacity: 0.8 }));
  scene.add(new THREE.Points(geo, mat));
}

function buildNodes(group, CSS2DObject) {
  const out = {};
  for (const n of DATA.nodes) {
    const hub = n.key === "orchestrator";
    const r = hub ? 0.36 : 0.2 + 0.12 * level(n.key);
    const holder = new THREE.Group();
    holder.position.set(n.pos[0], n.pos[1], n.pos[2]);

    const coreMat = track(new THREE.MeshBasicMaterial({ color: new THREE.Color(ACCENT).multiplyScalar(1.35) }));
    const core = new THREE.Mesh(track(new THREE.SphereGeometry(r, 24, 16)), coreMat);
    const shellMat = track(new THREE.LineBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.4 }));
    const shell = new THREE.LineSegments(
      track(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(r * 2.1, 1))), shellMat);
    const ringMat = track(new THREE.MeshBasicMaterial({
      color: ALARM, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false }));
    const ring = new THREE.Mesh(track(new THREE.RingGeometry(r * 1.5, r * 1.62, 64)), ringMat);
    holder.add(core, shell, ring);

    const div = document.createElement("div");
    const flagged = flaggedRecent(n.key) > 0;
    div.className = "lbl" + (flagged ? " bad" : "");
    const count = (DATA.activity || {})[n.key] || 0;
    div.innerHTML = "<b></b><span></span>";
    div.firstChild.textContent = n.label;
    div.lastChild.textContent = count + " ev" + (flagged ? " / " + flaggedRecent(n.key) + " flagged" : "");
    const label = new CSS2DObject(div);
    label.position.set(0, r * 2.4 + 0.22, 0);
    holder.add(label);

    group.add(holder);
    out[n.key] = { holder, core, shell, ring, coreMat, shellMat, ringMat, r, flagged,
                   phase: Math.random() * 6.28, rate: Math.min(2.2, 0.8 + flaggedRecent(n.key) * 0.25) };
  }
  return out;
}

function buildLinks(group, nodes) {
  const up = new THREE.Vector3(0, 1, 0);
  return DATA.links.map(([a, b]) => {
    const A = nodes[a].holder.position;
    const B = nodes[b].holder.position;
    const d = B.clone().sub(A);
    let side = new THREE.Vector3().crossVectors(d, up);
    if (side.lengthSq() < 1e-6) side = new THREE.Vector3(1, 0, 0);
    const mid = A.clone().add(B).multiplyScalar(0.5)
      .add(side.normalize().multiplyScalar(d.length() * 0.12)).add(new THREE.Vector3(0, 0.35, 0));
    const curve = new THREE.QuadraticBezierCurve3(A.clone(), mid, B.clone());
    const geo = track(new THREE.BufferGeometry().setFromPoints(curve.getPoints(40)));
    const mat = track(new THREE.LineBasicMaterial({ color: 0x2f6f9c, transparent: true, opacity: 0.5 }));
    group.add(new THREE.Line(geo, mat));
    return { a, b, curve };
  });
}

function buildParticles(group, links) {
  const parts = [];
  links.forEach((l, i) => {
    const rate = 0.12 + 0.88 * ((level(l.a) + level(l.b)) / 2);
    const hot = flaggedRecent(l.a) > 0 || flaggedRecent(l.b) > 0;
    const count = Math.round(3 + rate * 13);
    for (let j = 0; j < count; j++) {
      parts.push({ li: i, t: Math.random(), v: (0.05 + rate * 0.17) * (0.8 + Math.random() * 0.4),
                   alarm: hot && Math.random() < 0.35 });
    }
  });
  const pos = new Float32Array(parts.length * 3);
  const col = new Float32Array(parts.length * 3);
  const a = new THREE.Color(ACCENT).multiplyScalar(1.5);
  const b = new THREE.Color(ALARM).multiplyScalar(1.5);
  parts.forEach((p, i) => (p.alarm ? b : a).toArray(col, i * 3));
  const geo = track(new THREE.BufferGeometry());
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const mat = track(new THREE.PointsMaterial({
    size: 0.2, map: dotTexture(), vertexColors: true, transparent: true, depthWrite: false,
    blending: THREE.AdditiveBlending }));
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  group.add(points);
  const tmp = new THREE.Vector3();
  const step = (dt) => {
    parts.forEach((p, i) => {
      p.t = (p.t + p.v * dt) % 1;
      links[p.li].curve.getPoint(p.t, tmp);
      pos[i * 3] = tmp.x; pos[i * 3 + 1] = tmp.y; pos[i * 3 + 2] = tmp.z;
    });
    geo.attributes.position.needsUpdate = true;
  };
  step(0);
  return step;
}

function pulseNodes(nodes, t, camera) {
  const c = new THREE.Color();
  const alarm = new THREE.Color(ALARM);
  for (const n of Object.values(nodes)) {
    n.shell.rotation.y = t * 0.15 + n.phase;
    n.shell.rotation.x = t * 0.08;
    if (!n.flagged) continue;
    const k = (t * 0.55 * n.rate + n.phase) % 1;
    n.ring.quaternion.copy(camera.quaternion);
    n.ring.scale.setScalar(1 + k * 2.4);
    n.ringMat.opacity = (1 - k) * 0.8;
    const glow = 1.15 + 0.45 * Math.sin(t * 3 * n.rate + n.phase);
    n.coreMat.color.copy(c.copy(alarm).multiplyScalar(glow));
    n.shellMat.color.set(ALARM);
  }
}

async function start() {
  const base = "three/addons/";
  const [three, ec, rp, ub, op, oc, cr] = await Promise.all([
    import("three"),
    import(base + "postprocessing/EffectComposer.js"),
    import(base + "postprocessing/RenderPass.js"),
    import(base + "postprocessing/UnrealBloomPass.js"),
    import(base + "postprocessing/OutputPass.js"),
    import(base + "controls/OrbitControls.js"),
    import(base + "renderers/CSS2DRenderer.js"),
  ]);
  THREE = three;
  const size = () => [Math.max(stage.clientWidth, 10), Math.max(stage.clientHeight, 10)];
  let [w, h] = size();

  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h);
  renderer.setClearColor(VOID, 1);
  stage.appendChild(renderer.domElement);
  const labels = new cr.CSS2DRenderer();
  labels.setSize(w, h);
  labels.domElement.className = "labels";
  stage.appendChild(labels.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(VOID);
  scene.fog = new THREE.FogExp2(VOID, 0.026);
  const camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 120);
  camera.position.set(7.6, 3.8, 10.2);
  const controls = new oc.OrbitControls(camera, renderer.domElement);
  Object.assign(controls, { enableZoom: false, enablePan: false, enableDamping: true, dampingFactor: 0.06,
    autoRotate: !reduced, autoRotateSpeed: 0.45, minPolarAngle: Math.PI * 0.28, maxPolarAngle: Math.PI * 0.68 });

  const composer = new ec.EffectComposer(renderer);
  composer.setSize(w, h);
  composer.addPass(new rp.RenderPass(scene, camera));
  composer.addPass(new ub.UnrealBloomPass(new THREE.Vector2(w, h), 0.38, 0.4, 0.45));
  composer.addPass(new op.OutputPass());

  buildBackdrop(scene);
  const group = new THREE.Group();
  const cx = DATA.nodes.reduce((s, n) => s + n.pos[0], 0) / DATA.nodes.length;
  group.position.x = -cx;
  scene.add(group);
  const nodes = buildNodes(group, cr.CSS2DObject);
  const stepParticles = buildParticles(group, buildLinks(group, nodes));

  const clock = new THREE.Clock();
  let raf = 0;
  let running = false;
  const draw = () => {
    controls.update();
    pulseNodes(nodes, clock.elapsedTime, camera);
    composer.render();
    labels.render(scene, camera);
  };
  const frame = () => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(clock.getDelta(), 0.05);
    stepParticles(dt);
    draw();
  };
  const setRunning = (on) => {
    if (on && !running && !reduced) { running = true; clock.getDelta(); frame(); }
    if (!on && running) { running = false; cancelAnimationFrame(raf); }
  };
  if (reduced) controls.addEventListener("change", draw);
  draw();

  const onResize = () => {
    [w, h] = size();
    renderer.setSize(w, h);
    composer.setSize(w, h);
    labels.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    draw();
  };
  const ro = new ResizeObserver(onResize);
  ro.observe(stage);
  const io = new IntersectionObserver((e) => setRunning(e[0].isIntersecting && !document.hidden));
  io.observe(stage);
  const onVis = () => setRunning(!document.hidden);
  document.addEventListener("visibilitychange", onVis);

  const teardown = () => {
    setRunning(false);
    ro.disconnect(); io.disconnect();
    document.removeEventListener("visibilitychange", onVis);
    controls.dispose();
    disposables.forEach((d) => d.dispose && d.dispose());
    composer.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
  };
  window.addEventListener("pagehide", teardown, { once: true });
  document.body.classList.add("ready");
}

if (!hasWebGL()) {
  showFallback("WebGL is not available in this browser. Showing the static map.");
} else {
  try {
    await start();
  } catch (e) {
    console.error(e);
    showFallback("The 3D view could not load. Showing the static map.");
  }
}
