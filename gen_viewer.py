"""Generate multi-resolution 360 viewer with inertia from existing images."""
import json
import os

base_dir = r"C:\Users\ParkBakery\Desktop\TestOutputFolder\360\box3"
barcode = "box3"

with open(os.path.join(base_dir, "_size_map.json"), "r") as f:
    size_map = json.load(f)

n_frames = len(size_map["M"])

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>360 View - """ + barcode + """</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1a1a2e; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; font-family: 'Segoe UI', sans-serif; color: #e2e4ed; }
h1 { margin-bottom: 16px; font-size: 20px; font-weight: 400; color: #6b7394; }
h1 span { color: #6c8cff; font-weight: 600; }
.viewer { position: relative; cursor: grab; user-select: none; border: 2px solid #2e3348; border-radius: 8px; overflow: hidden; background: #fff; touch-action: none; }
canvas { display: block; }
.hint { margin-top: 16px; color: #4a5170; font-size: 13px; }
.controls { display: flex; gap: 16px; margin-top: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }
.bar { display: flex; gap: 4px; margin-top: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: #2e3348; transition: background 0.1s; }
.dot.a { background: #6c8cff; }
.info { margin-top: 10px; color: #4a5170; font-size: 12px; }
.zoom-bar { display: flex; align-items: center; gap: 8px; }
.zoom-bar button { background: #2e3348; color: #e2e4ed; border: none; border-radius: 4px; width: 30px; height: 30px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.zoom-bar button:hover { background: #6c8cff; }
.zoom-label { font-size: 13px; color: #6b7394; min-width: 50px; text-align: center; }
.zoom-slider { -webkit-appearance: none; width: 100px; height: 4px; background: #2e3348; border-radius: 2px; outline: none; }
.zoom-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: #6c8cff; cursor: pointer; }
.loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); color: #6c8cff; font-size: 14px; z-index: 10; }
.res-bar { display: flex; gap: 4px; align-items: center; }
.res-bar span { font-size: 11px; color: #6b7394; margin-right: 4px; }
.res-btn { background: #2e3348; color: #8890a8; border: none; border-radius: 4px; padding: 5px 12px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.res-btn:hover { background: #3a4060; color: #e2e4ed; }
.res-btn.active { background: #6c8cff; color: #fff; }
</style>
</head>
<body>
<h1>360&deg; <span>""" + barcode + """</span></h1>
<div class="viewer" id="viewer">
    <canvas id="cv"></canvas>
    <div class="loading" id="loading">Loading 0%</div>
</div>
<p class="hint">Drag = Rotate (with momentum) &nbsp;|&nbsp; Scroll = Zoom &nbsp;|&nbsp; Double-click = Reset</p>
<div class="controls">
    <div class="zoom-bar">
        <button id="zo" title="Zoom Out">&minus;</button>
        <input type="range" class="zoom-slider" id="zs" min="100" max="500" value="100">
        <button id="zi" title="Zoom In">+</button>
        <span class="zoom-label" id="zl">100%</span>
    </div>
    <div class="res-bar">
        <span>Quality:</span>
        <button class="res-btn" data-sz="S">S <small>(480px)</small></button>
        <button class="res-btn" data-sz="M">M <small>(800px)</small></button>
        <button class="res-btn active" data-sz="L">L <small>(1200px)</small></button>
        <button class="res-btn" data-sz="OG">OG</button>
    </div>
</div>
<div class="bar" id="bar"></div>
<p class="info" id="info">Frame 1 / """ + str(n_frames) + """</p>
<script>
(function(){
const SIZE_MAP = """ + json.dumps(size_map) + """;
let curSize = 'L';
let SRC = SIZE_MAP[curSize];
const N = SRC.length;

// Canvas size — auto-adapts to image aspect ratio
const MAX_CW = 900;
let CW = MAX_CW, CH = MAX_CW;
let aspectDetected = false;

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const viewer = document.getElementById('viewer');
const info = document.getElementById('info');
const bar = document.getElementById('bar');
const loadEl = document.getElementById('loading');
const slider = document.getElementById('zs');
const zLabel = document.getElementById('zl');

cv.width = CW; cv.height = CH;

// ── Preload frames per size ──
let frames = new Array(N);
const dots = [];
const frameCache = {};

for (let i = 0; i < N; i++) {
    const d = document.createElement('div');
    d.className = 'dot' + (i === 0 ? ' a' : '');
    bar.appendChild(d);
    dots.push(d);
}

function adaptCanvas(bmp) {
    if (aspectDetected) return;
    aspectDetected = true;
    var iw = bmp.width, ih = bmp.height;
    if (iw > 0 && ih > 0) {
        var ratio = ih / iw;
        CW = Math.min(MAX_CW, Math.max(600, iw));
        CH = Math.round(CW * ratio);
        if (CH > 800) { CH = 800; CW = Math.round(CH / ratio); }
        if (CH < 300) { CH = 300; CW = Math.round(CH / ratio); }
        cv.width = CW; cv.height = CH;
    }
}

function loadSize(sz, onDone) {
    if (frameCache[sz]) {
        frames = frameCache[sz];
        if (onDone) onDone();
        return;
    }
    const arr = new Array(N);
    let cnt = 0;
    loadEl.style.display = '';
    loadEl.textContent = 'Loading ' + sz + ' 0%';
    const srcs = SIZE_MAP[sz];
    for (let i = 0; i < N; i++) {
        const im = new Image();
        im.src = srcs[i];
        im.onload = (function(idx) {
            return function() {
                createImageBitmap(im).then(function(bmp) {
                    if (idx === 0) adaptCanvas(bmp);
                    arr[idx] = bmp;
                    cnt++;
                    loadEl.textContent = 'Loading ' + sz + ' ' + Math.round(cnt/N*100) + '%';
                    if (cnt === N) {
                        frameCache[sz] = arr;
                        frames = arr;
                        loadEl.style.display = 'none';
                        if (onDone) onDone();
                    }
                });
            };
        })(i);
    }
}

loadSize('L', function() { draw(); });

// ── Resolution switcher ──
var resButtons = document.querySelectorAll('.res-btn');
resButtons.forEach(function(btn) {
    btn.addEventListener('click', function() {
        var sz = this.dataset.sz;
        if (sz === curSize) return;
        curSize = sz;
        SRC = SIZE_MAP[sz];
        resButtons.forEach(function(b) { b.classList.remove('active'); });
        this.classList.add('active');
        loadSize(sz, function() { draw(); });
    });
});

// ── State ──
var cur = 0, zoom = 1, panX = 0, panY = 0;
var dirty = true;

function draw() {
    if (!frames[cur]) return;
    ctx.setTransform(1,0,0,1,0,0);
    ctx.clearRect(0, 0, CW, CH);
    ctx.setTransform(zoom, 0, 0, zoom, panX, panY);
    var f = frames[cur];
    // Fill canvas completely — no letterboxing
    var scale = Math.max(CW / f.width, CH / f.height);
    var w = f.width * scale, h = f.height * scale;
    var x = (CW - w) / 2, y = (CH - h) / 2;
    ctx.drawImage(f, x, y, w, h);
    dirty = false;
}

function schedDraw() {
    if (!dirty) { dirty = true; requestAnimationFrame(draw); }
}

function show(idx) {
    cur = ((idx % N) + N) % N;
    info.textContent = 'Frame ' + (cur+1) + ' / ' + N;
    for (var i = 0; i < N; i++) dots[i].className = i === cur ? 'dot a' : 'dot';
    schedDraw();
}

// ── Zoom ──
var ZMIN = 1, ZMAX = 5;

function applyZoomUI() {
    var p = Math.round(zoom * 100);
    slider.value = p;
    zLabel.textContent = p + '%';
    viewer.style.cursor = zoom > 1 ? 'move' : 'grab';
}

function zoomAt(nz, cx, cy) {
    nz = Math.min(ZMAX, Math.max(ZMIN, nz));
    var ix = (cx - panX) / zoom;
    var iy = (cy - panY) / zoom;
    panX = cx - ix * nz;
    panY = cy - iy * nz;
    zoom = nz;
    if (zoom <= 1) { zoom = 1; panX = 0; panY = 0; }
    applyZoomUI(); schedDraw();
}

function zoomCtr(nz) { zoomAt(nz, CW/2, CH/2); }

// ── Inertia physics ──
var dragging = false, panning = false, lastX = 0, lastY = 0;
var velocity = 0, lastMoveTime = 0, accumDx = 0;
var inertiaRaf = 0;
var FRICTION = 0.92;
var VEL_SCALE = 0.3;
var VEL_MIN = 0.08;

function stopInertia() { cancelAnimationFrame(inertiaRaf); inertiaRaf = 0; velocity = 0; }

function startInertia() {
    if (Math.abs(velocity) < VEL_MIN) return;
    function tick() {
        velocity *= FRICTION;
        if (Math.abs(velocity) < VEL_MIN) { velocity = 0; return; }
        accumDx += velocity;
        var steps = Math.trunc(accumDx);
        if (steps !== 0) {
            show(cur + steps);
            accumDx -= steps;
        }
        inertiaRaf = requestAnimationFrame(tick);
    }
    accumDx = 0;
    inertiaRaf = requestAnimationFrame(tick);
}

// ── Auto-play ──
var autoplay = null, autoDelay = null;
function stopAuto() { clearTimeout(autoDelay); clearInterval(autoplay); autoplay = null; autoDelay = null; }

// ── Mouse drag + inertia ──
viewer.addEventListener('mousedown', function(e) {
    stopInertia();
    stopAuto();
    if (zoom > 1) {
        panning = true;
    } else {
        dragging = true;
        velocity = 0;
        lastMoveTime = performance.now();
    }
    lastX = e.clientX; lastY = e.clientY;
    e.preventDefault();
});

window.addEventListener('mousemove', function(e) {
    if (dragging) {
        var now = performance.now();
        var dx = e.clientX - lastX;
        var sens = Math.max(3, Math.round(CW / N));
        velocity = (dx / sens) * VEL_SCALE;
        velocity = Math.max(-4, Math.min(4, velocity));
        if (Math.abs(dx) > sens) {
            show(cur + (dx > 0 ? 1 : -1));
            lastX = e.clientX;
        }
        lastMoveTime = now;
    } else if (panning) {
        panX += e.clientX - lastX;
        panY += e.clientY - lastY;
        lastX = e.clientX; lastY = e.clientY;
        applyZoomUI(); schedDraw();
    }
});

window.addEventListener('mouseup', function() {
    if (dragging) {
        dragging = false;
        if (performance.now() - lastMoveTime < 100) {
            startInertia();
        }
    }
    panning = false;
});

// ── Touch + inertia + pinch-zoom ──
var pinching = false, pinchDist = 0, pinchZoom = 1;
function getTouchDist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }
function getTouchCenter(t) { return [(t[0].clientX + t[1].clientX) / 2, (t[0].clientY + t[1].clientY) / 2]; }

viewer.addEventListener('touchstart', function(e) {
    stopAuto(); stopInertia();
    if (e.touches.length === 2) {
        pinching = true; dragging = false; panning = false;
        pinchDist = getTouchDist(e.touches);
        pinchZoom = zoom;
        e.preventDefault(); return;
    }
    pinching = false;
    if (zoom > 1) { panning = true; } else {
        dragging = true; velocity = 0; lastMoveTime = performance.now();
    }
    lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
}, { passive: false });

window.addEventListener('touchmove', function(e) {
    if (pinching && e.touches.length === 2) {
        e.preventDefault();
        var nd = getTouchDist(e.touches);
        var center = getTouchCenter(e.touches);
        var rect = cv.getBoundingClientRect();
        zoomAt(pinchZoom * nd / pinchDist,
               (center[0] - rect.left) * (CW / rect.width),
               (center[1] - rect.top) * (CH / rect.height));
        return;
    }
    if (dragging) {
        var dx = e.touches[0].clientX - lastX;
        var sens = Math.max(3, Math.round(CW / N));
        velocity = (dx / sens) * VEL_SCALE;
        velocity = Math.max(-4, Math.min(4, velocity));
        if (Math.abs(dx) > sens) { show(cur + (dx > 0 ? 1 : -1)); lastX = e.touches[0].clientX; }
        lastMoveTime = performance.now();
    } else if (panning) {
        panX += e.touches[0].clientX - lastX;
        panY += e.touches[0].clientY - lastY;
        lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
        applyZoomUI(); schedDraw();
    }
}, { passive: false });

window.addEventListener('touchend', function(e) {
    if (e.touches.length < 2) pinching = false;
    if (e.touches.length === 0) {
        if (dragging && performance.now() - lastMoveTime < 100) startInertia();
        dragging = false; panning = false;
    }
});

// ── Scroll zoom ──
viewer.addEventListener('wheel', function(e) {
    e.preventDefault(); stopAuto(); stopInertia();
    var rect = cv.getBoundingClientRect();
    var f = 1.12;
    zoomAt(e.deltaY < 0 ? zoom * f : zoom / f,
           (e.clientX - rect.left) * (CW / rect.width),
           (e.clientY - rect.top) * (CH / rect.height));
}, { passive: false });

// ── Buttons ──
document.getElementById('zi').addEventListener('click', function() { zoomCtr(zoom * 1.3); });
document.getElementById('zo').addEventListener('click', function() { zoomCtr(zoom / 1.3); });
slider.addEventListener('input', function() { zoomCtr(parseInt(slider.value) / 100); });

viewer.addEventListener('dblclick', function() {
    zoom = 1; panX = 0; panY = 0; stopInertia();
    applyZoomUI(); schedDraw();
});

// ── Keyboard ──
window.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') { stopInertia(); show(cur - 1); }
    else if (e.key === 'ArrowRight') { stopInertia(); show(cur + 1); }
    else if (e.key === '+' || e.key === '=') zoomCtr(zoom * 1.15);
    else if (e.key === '-') zoomCtr(zoom / 1.15);
    else if (e.key === '0') { zoom = 1; panX = 0; panY = 0; stopInertia(); applyZoomUI(); schedDraw(); }
    else if (e.key === '1') document.querySelector('[data-sz="S"]').click();
    else if (e.key === '2') document.querySelector('[data-sz="M"]').click();
    else if (e.key === '3') document.querySelector('[data-sz="L"]').click();
    else if (e.key === '4') document.querySelector('[data-sz="OG"]').click();
});

// ── Auto-play hover ──
viewer.addEventListener('mouseenter', function() {
    if (zoom <= 1 && !dragging && velocity === 0) {
        autoDelay = setTimeout(function() {
            if (!dragging && !panning && zoom <= 1 && velocity === 0)
                autoplay = setInterval(function() { show(cur + 1); }, 120);
        }, 800);
    }
});
viewer.addEventListener('mouseleave', stopAuto);
viewer.addEventListener('mousedown', stopAuto);

})();
</script>
</body>
</html>"""

viewer_path = os.path.join(base_dir, "viewer.html")
with open(viewer_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Viewer saved: {viewer_path}")
