const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));

const STORE_KEY = 'touring-app-v1';
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const state = {
  tab: 'near',
  pos: null,
  city: 'london',
  farFromData: false,
  filters: { when: 'all', cat: 'all', max: 9999 },
  view: 'list',
  mode: 'identify',
  detailId: null,
  inviteContext: null,
  map: null,
  markers: null,
  stream: null,
  ...load()
};

function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) { /* private mode or blocked storage */ }
  return { saved: [], itinerary: [], invitesOut: [], invitesIn: null };
}

function save() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
      saved: state.saved, itinerary: state.itinerary,
      invitesOut: state.invitesOut, invitesIn: state.invitesIn
    }));
  } catch (e) { /* storage unavailable — session-only is acceptable */ }
}

if (!state.saved) state.saved = [];
if (!state.itinerary) state.itinerary = [];
if (!state.invitesOut) state.invitesOut = [];
if (state.invitesIn === null || state.invitesIn === undefined) {
  state.invitesIn = [
    { id: 'seed-1', eventId: 'ldn-2', from: 'Maya', status: 'pending' },
    { id: 'seed-2', eventId: 'par-2', from: 'Tom', status: 'accepted' }
  ];
}

/* ---------------- geo + dates ---------------- */

function haversine(a1, o1, a2, o2) {
  const R = 6371, r = Math.PI / 180;
  const dLat = (a2 - a1) * r, dLon = (o2 - o1) * r;
  const h = Math.sin(dLat/2)**2 + Math.cos(a1*r) * Math.cos(a2*r) * Math.sin(dLon/2)**2;
  return R * 2 * Math.asin(Math.sqrt(h));
}

function fmtDist(km) {
  if (km == null) return '';
  if (km < 1) return Math.round(km * 1000) + ' m';
  if (km < 100) return km.toFixed(1) + ' km';
  return Math.round(km).toLocaleString() + ' km';
}

function dateFor(offset) {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + offset);
  return d;
}

function fmtWhen(ev) {
  const d = dateFor(ev.dayOffset);
  const today = new Date(); today.setHours(0,0,0,0);
  const diff = Math.round((d - today) / 86400000);
  let day;
  if (diff === 0) day = 'Today';
  else if (diff === 1) day = 'Tomorrow';
  else if (diff < 7) day = d.toLocaleDateString(undefined, { weekday: 'long' });
  else day = d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
  return day + ' · ' + ev.time;
}

function fmtPrice(ev) {
  if (ev.price === 0) return { text: 'Free', free: true };
  const cur = CITIES[ev.city].currency;
  return { text: cur + ev.price.toLocaleString(), free: false };
}

/* --------- data layer: replace this with live provider feeds --------- */

function getEvents() {
  return EVENTS.map((ev) => {
    const dist = state.pos ? haversine(state.pos.lat, state.pos.lng, ev.lat, ev.lng) : null;
    return { ...ev, dist, date: dateFor(ev.dayOffset) };
  });
}

function getEvent(id) { return getEvents().find((e) => e.id === id); }

function nearbyEvents() {
  let list = getEvents().filter((e) => e.city === state.city);

  const f = state.filters;
  if (f.cat !== 'all') list = list.filter((e) => e.category === f.cat);
  if (f.max === 0) list = list.filter((e) => e.price === 0);
  else if (f.max < 9999) list = list.filter((e) => e.price <= f.max);

  if (f.when === 'today') list = list.filter((e) => e.dayOffset === 0);
  else if (f.when === 'weekend') list = list.filter((e) => [0, 6].includes(e.date.getDay()) && e.dayOffset <= 13);
  else if (f.when === 'month') list = list.filter((e) => e.date.getMonth() === new Date().getMonth());

  return list.sort((a, b) => (a.dist != null ? a.dist - b.dist : a.dayOffset - b.dayOffset));
}

/* ---------------- shell ---------------- */

const TITLES = {
  near: 'Near Me', discover: 'Discover', plan: 'Plan a Trip',
  invites: 'Invites', detail: 'Event', about: 'About'
};

function go(tab, opts = {}) {
  if (tab !== 'discover') stopCamera();
  state.tab = tab;
  $$('.screen').forEach((s) => s.classList.remove('active'));
  $('#screen-' + tab).classList.add('active');
  $$('.tabbar button').forEach((b) => b.classList.toggle('on', b.dataset.tab === tab));
  $('#backBtn').hidden = !['detail', 'about'].includes(tab);
  $('#title').firstChild.textContent = TITLES[tab];
  $('#subtitle').textContent = opts.sub || defaultSub(tab);
  window.scrollTo(0, 0);
  if (tab === 'near') renderNear();
  if (tab === 'discover') renderDiscover();
  if (tab === 'plan') renderPlan();
  if (tab === 'invites') renderInvites();
}

function defaultSub(tab) {
  const city = CITIES[state.city].name;
  if (tab === 'near') return state.pos ? (state.farFromData ? 'Showing ' + city : 'Around you · ' + city) : 'Location off · ' + city;
  if (tab === 'discover') return state.mode === 'translate' ? 'Translate what you see' : 'Point, shoot, find out';
  if (tab === 'plan') return 'What will be on when you go';
  if (tab === 'invites') return 'Who you asked, who said yes';
  return '';
}

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove('show'), 2400);
}

function openSheet(html) {
  $('#sheet').innerHTML = '<div class="grab"></div>' + html;
  $('#sheet').classList.add('open');
  $('#backdrop').classList.add('open');
}
function closeSheet() {
  $('#sheet').classList.remove('open');
  $('#backdrop').classList.remove('open');
}

/* ---------------- location ---------------- */

function initLocation() {
  if (!navigator.geolocation) return locFailed('This browser does not support location.');
  navigator.geolocation.getCurrentPosition(
    (p) => {
      state.pos = { lat: p.coords.latitude, lng: p.coords.longitude };
      let best = null, bestD = Infinity;
      for (const [key, c] of Object.entries(CITIES)) {
        const d = haversine(state.pos.lat, state.pos.lng, c.lat, c.lng);
        if (d < bestD) { bestD = d; best = key; }
      }
      state.city = best;
      state.farFromData = bestD > 120;
      $('#subtitle').textContent = defaultSub(state.tab);
      renderNear();
    },
    () => locFailed('Location permission denied.'),
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
  );
}

function locFailed(msg) {
  state.pos = null;
  $('#subtitle').textContent = defaultSub(state.tab);
  renderNear(msg);
}

/* ---------------- Near Me ---------------- */

function eventCard(ev) {
  const cat = CATEGORIES[ev.category];
  const p = fmtPrice(ev);
  return `<button class="card" data-event="${esc(ev.id)}">
    <div class="card-img" style="background:linear-gradient(135deg,${cat.c1},${cat.c2})">
      <span class="glyph">${cat.icon}</span>
      <span class="cat">${esc(cat.label)}</span>
      ${ev.dist != null ? `<span class="dist">${fmtDist(ev.dist)}</span>` : ''}
    </div>
    <div class="card-body">
      <h3>${esc(ev.title)}</h3>
      <div class="card-meta">${esc(ev.venue)}</div>
      <div class="card-foot">
        <span class="when">${esc(fmtWhen(ev))}</span>
        <span class="price ${p.free ? 'free' : ''}">${esc(p.text)}</span>
      </div>
    </div>
  </button>`;
}

function renderNear(errMsg) {
  const banner = $('#locBanner');
  if (!state.pos) {
    banner.innerHTML = `<div class="banner"><strong>${esc(errMsg || 'Location unavailable.')}</strong>
      Pick a city to browse instead.</div>
      <label for="cityPick">City</label>
      <select id="cityPick">${Object.entries(CITIES).map(([k, c]) =>
        `<option value="${k}" ${k === state.city ? 'selected' : ''}>${esc(c.name)}, ${esc(c.country)}</option>`).join('')}</select>`;
    $('#cityPick').onchange = (e) => { state.city = e.target.value; go('near'); };
  } else if (state.farFromData) {
    banner.innerHTML = `<div class="banner">You're a long way from this prototype's demo cities, so we're showing
      <strong>${esc(CITIES[state.city].name)}</strong> — the closest one. Distances are still measured from where you actually are.</div>`;
  } else {
    banner.innerHTML = `<div class="banner">Showing events around <strong>${esc(CITIES[state.city].name)}</strong>, sorted by how close they are to you.</div>`;
  }

  const list = nearbyEvents();
  const el = $('#nearList');
  if (state.view === 'map') {
    el.hidden = true; $('#map').hidden = false; drawMap(list);
  } else {
    $('#map').hidden = true; el.hidden = false;
    el.innerHTML = list.length
      ? list.map(eventCard).join('')
      : `<div class="empty"><div class="big">◎</div>Nothing matches those filters.<br>Try widening the date or price.</div>`;
  }
}

const TILES = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const mapsReady = () => typeof L !== 'undefined';

function mapUnavailable(id) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="empty" style="padding:28px 16px"><div class="big">▦</div>
    Map couldn't load.<br><span style="font-size:12px">Check your connection — everything else still works.</span></div>`;
}

function drawMap(list) {
  if (!mapsReady()) return mapUnavailable('map');
  if (!state.map) {
    state.map = L.map('map', { zoomControl: false }).setView([CITIES[state.city].lat, CITIES[state.city].lng], 12);
    L.tileLayer(TILES, { attribution: '© OpenStreetMap, © CARTO', maxZoom: 19 }).addTo(state.map);
    state.markers = L.layerGroup().addTo(state.map);
  }
  state.markers.clearLayers();
  const pts = [];
  list.forEach((ev) => {
    const cat = CATEGORIES[ev.category];
    const icon = L.divIcon({
      className: '',
      html: `<div style="background:linear-gradient(135deg,${cat.c1},${cat.c2});width:30px;height:30px;border-radius:50%;
             display:grid;place-items:center;color:#fff;font-size:14px;border:2px solid rgba(255,255,255,.85);
             box-shadow:0 2px 8px rgba(0,0,0,.5)">${cat.icon}</div>`,
      iconSize: [30, 30], iconAnchor: [15, 15]
    });
    const m = L.marker([ev.lat, ev.lng], { icon }).addTo(state.markers);
    m.bindPopup(`<strong>${esc(ev.title)}</strong><br>${esc(fmtWhen(ev))} · ${esc(fmtPrice(ev).text)}`);
    m.on('click', () => setTimeout(() => showDetail(ev.id), 600));
    pts.push([ev.lat, ev.lng]);
  });
  if (state.pos) {
    L.circleMarker([state.pos.lat, state.pos.lng], {
      radius: 8, color: '#fff', weight: 3, fillColor: '#fbbf24', fillOpacity: 1
    }).addTo(state.markers).bindPopup('You are here');
    if (!state.farFromData) pts.push([state.pos.lat, state.pos.lng]);
  }
  setTimeout(() => {
    state.map.invalidateSize();
    if (pts.length) state.map.fitBounds(pts, { padding: [40, 40], maxZoom: 14 });
  }, 60);
}

/* ---------------- Event detail ---------------- */

function showDetail(id, invite) {
  const ev = getEvent(id);
  if (!ev) return;
  state.detailId = id;
  state.inviteContext = invite || null;
  const cat = CATEGORIES[ev.category];
  const p = fmtPrice(ev);
  const c = CITIES[ev.city];
  const isSaved = state.saved.includes(id);

  $('#screen-detail').innerHTML = `
    <div class="detail-hero" style="background:linear-gradient(135deg,${cat.c1},${cat.c2})">
      <span class="glyph">${cat.icon}</span>
    </div>
    <div class="detail-body">
      ${invite ? `<div class="banner invite" style="margin-top:16px">
        <strong>${esc(invite.from)} invited you.</strong> Let them know if you can make it.</div>` : ''}
      <h2>${esc(ev.title)}</h2>
      <div class="detail-meta">${esc(ev.venue)} · ${esc(c.name)}${ev.dist != null ? ' · ' + fmtDist(ev.dist) + ' away' : ''}</div>

      <div class="factgrid">
        <div class="fact"><div class="k">When</div><div class="v">${esc(fmtWhen(ev))}</div></div>
        <div class="fact"><div class="k">Cost</div><div class="v ${p.free ? 'price free' : ''}">${esc(p.text)}</div></div>
        <div class="fact"><div class="k">Category</div><div class="v">${esc(cat.label)}</div></div>
        <div class="fact"><div class="k">Runs for</div><div class="v">${ev.hours} hrs</div></div>
      </div>

      <p class="prose">${esc(ev.description)}</p>
      <div class="minimap" id="detailMap"></div>

      ${invite ? `<div class="btn-row" style="margin-bottom:10px">
        <button class="btn" data-rsvp="accepted">Accept</button>
        <button class="btn secondary" data-rsvp="declined">Decline</button>
      </div>` : ''}

      <a class="btn" href="#" id="ticketBtn">${p.free ? 'Register — free' : 'Get tickets · ' + esc(p.text)}</a>
      <button class="btn secondary" id="inviteBtn">Invite friends</button>
      <button class="btn secondary" id="saveBtn">${isSaved ? 'Saved ✓' : 'Save event'}</button>
      <button class="btn secondary" id="addTripBtn">Add to itinerary</button>
      <div class="sim-note">Organised by ${esc(ev.organizer)}. This is seeded demo data in a prototype —
      the ticket link is a placeholder, not a real booking page.</div>
    </div>`;

  go('detail', { sub: c.name });

  $('#ticketBtn').onclick = (e) => { e.preventDefault(); toast('Placeholder — no real booking in this prototype'); };
  $('#inviteBtn').onclick = () => inviteSheet(ev);
  $('#saveBtn').onclick = (e) => {
    const i = state.saved.indexOf(id);
    if (i >= 0) { state.saved.splice(i, 1); e.target.textContent = 'Save event'; toast('Removed'); }
    else { state.saved.push(id); e.target.textContent = 'Saved ✓'; toast('Saved'); }
    save();
  };
  $('#addTripBtn').onclick = () => {
    if (!state.itinerary.includes(id)) { state.itinerary.push(id); save(); toast('Added to your itinerary'); }
    else toast('Already in your itinerary');
  };
  $$('[data-rsvp]').forEach((b) => {
    b.onclick = () => {
      const inv = state.invitesIn.find((x) => x.id === invite.id);
      if (inv) { inv.status = b.dataset.rsvp; save(); }
      toast(b.dataset.rsvp === 'accepted' ? "You're going" : 'Declined');
      go('invites');
    };
  });

  if (!mapsReady()) return mapUnavailable('detailMap');
  try {
    const dm = L.map('detailMap', { zoomControl: false, dragging: false, scrollWheelZoom: false })
      .setView([ev.lat, ev.lng], 14);
    L.tileLayer(TILES, { maxZoom: 19 }).addTo(dm);
    L.circleMarker([ev.lat, ev.lng], { radius: 9, color: '#fff', weight: 3, fillColor: cat.c1, fillOpacity: 1 }).addTo(dm);
    setTimeout(() => dm.invalidateSize(), 60);
  } catch (e) { mapUnavailable('detailMap'); }
}

/* ---------------- Invites ---------------- */

function inviteLink(eventId, from) {
  const base = location.origin + location.pathname;
  return `${base}#invite=${encodeURIComponent(eventId)}&from=${encodeURIComponent(from || 'A friend')}`;
}

function inviteSheet(ev) {
  openSheet(`
    <h3>Invite to ${esc(ev.title)}</h3>
    <div class="sheet-sub">${esc(fmtWhen(ev))} · ${esc(ev.venue)}</div>
    <label for="fromName">Your name</label>
    <input id="fromName" placeholder="e.g. Sam" value="${esc(localStorage.getItem('touring-name') || '')}">
    <label for="guestNames">Who are you inviting?</label>
    <input id="guestNames" placeholder="Separate names with commas">
    <button class="btn" id="sendInvite">Send invites</button>
    <button class="btn secondary" id="shareLink">Share a link instead</button>
    <div class="sim-note">Invites are stored in this browser. A real build would deliver them by
    push notification and email, and track replies server-side.</div>`);

  $('#sendInvite').onclick = () => {
    const from = ($('#fromName').value || '').trim() || 'You';
    const guests = ($('#guestNames').value || '').split(',').map((s) => s.trim()).filter(Boolean);
    if (!guests.length) return toast('Add at least one name');
    localStorage.setItem('touring-name', from);
    state.invitesOut.push({
      id: 'inv-' + Date.now(), eventId: ev.id, from,
      guests: guests.map((n) => ({ name: n, status: 'pending' }))
    });
    save();
    closeSheet();
    toast(`Invited ${guests.length} ${guests.length === 1 ? 'person' : 'people'}`);
    go('invites');
  };

  $('#shareLink').onclick = async () => {
    const from = ($('#fromName').value || '').trim() || 'A friend';
    const url = inviteLink(ev.id, from);
    const text = `${from} invited you to ${ev.title} — ${fmtWhen(ev)} at ${ev.venue}`;
    try {
      if (navigator.share) { await navigator.share({ title: ev.title, text, url }); closeSheet(); return; }
      await navigator.clipboard.writeText(url);
      toast('Invite link copied');
      closeSheet();
    } catch (e) { /* user dismissed the share sheet */ }
  };
}

function renderInvites() {
  const inEl = $('#invitesIn');
  inEl.innerHTML = state.invitesIn.length ? state.invitesIn.map((inv) => {
    const ev = getEvent(inv.eventId);
    if (!ev) return '';
    return `<div class="invite-row">
      <h4>${esc(ev.title)}</h4>
      <div class="who">From ${esc(inv.from)} · ${esc(fmtWhen(ev))}</div>
      <div class="guest">
        <button data-open="${esc(ev.id)}" data-inv="${esc(inv.id)}" style="color:var(--accent);font-weight:700">View event</button>
        <span class="status ${esc(inv.status)}">${esc(inv.status)}</span>
      </div>
    </div>`;
  }).join('') : `<div class="empty"><div class="big">✉</div>No invites yet.</div>`;

  const outEl = $('#invitesOut');
  outEl.innerHTML = state.invitesOut.length ? state.invitesOut.map((inv) => {
    const ev = getEvent(inv.eventId);
    if (!ev) return '';
    return `<div class="invite-row">
      <h4>${esc(ev.title)}</h4>
      <div class="who">${esc(fmtWhen(ev))} · ${inv.guests.length} invited</div>
      ${inv.guests.map((g, i) => `<div class="guest">
        <span>${esc(g.name)}</span>
        <button data-sim="${esc(inv.id)}|${i}"><span class="status ${esc(g.status)}">${esc(g.status)}</span></button>
      </div>`).join('')}
    </div>`;
  }).join('') : `<div class="empty"><div class="big">✦</div>You haven't invited anyone yet.<br>Open an event and tap Invite friends.</div>`;

  $$('[data-open]').forEach((b) => b.onclick = () => {
    const inv = state.invitesIn.find((x) => x.id === b.dataset.inv);
    showDetail(b.dataset.open, inv);
  });
  $$('[data-sim]').forEach((b) => b.onclick = () => {
    const [invId, idx] = b.dataset.sim.split('|');
    const inv = state.invitesOut.find((x) => x.id === invId);
    const g = inv.guests[+idx];
    g.status = g.status === 'pending' ? 'accepted' : g.status === 'accepted' ? 'declined' : 'pending';
    save();
    renderInvites();
  });
}

/* ---------------- Discover (camera) ---------------- */

function renderDiscover() {
  $('#discoverBlurb').textContent = state.mode === 'translate'
    ? 'Photograph a menu, sign or plaque and get it translated into English.'
    : 'Photograph a landmark, building or artwork. We identify it, tell you its story, and show you what is on nearby.';
  $('#discoverIntro').hidden = false;
  $('#discoverResult').hidden = true;
  $('#shutterBtn').hidden = !state.stream;
}

async function startCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } }, audio: false
    });
    const v = document.createElement('video');
    v.autoplay = true; v.playsInline = true; v.muted = true;
    v.srcObject = state.stream;
    $('#cameraStage').innerHTML = '';
    $('#cameraStage').appendChild(v);
    $('#shutterBtn').hidden = false;
    $('#startCamBtn').hidden = true;
  } catch (e) {
    toast('Camera unavailable — choose a photo instead');
  }
}

function stopCamera() {
  if (state.stream) { state.stream.getTracks().forEach((t) => t.stop()); state.stream = null; }
  const b = $('#startCamBtn'); if (b) b.hidden = false;
  const s = $('#shutterBtn'); if (s) s.hidden = true;
}

function capture() {
  const v = $('#cameraStage video');
  if (!v) return;
  const c = document.createElement('canvas');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  const url = c.toDataURL('image/jpeg', 0.85);
  stopCamera();
  analyse(url);
}

function analyse(imgUrl) {
  $('#cameraStage').innerHTML = `<img src="${imgUrl}" alt="">
    <div class="scanning"><div class="scanline"></div></div>`;
  $('#shutterBtn').hidden = true;
  setTimeout(() => (state.mode === 'translate' ? showTranslation(imgUrl) : showIdentification(imgUrl)), 1700);
}

function showIdentification(imgUrl) {
  const lm = LANDMARKS[state.city];
  const related = lm.relatedEvents.map(getEvent).filter(Boolean);
  $('#discoverIntro').hidden = true;
  $('#discoverResult').hidden = false;
  $('#discoverResult').innerHTML = `
    <div class="camera-stage" style="aspect-ratio:16/10"><img src="${imgUrl}" alt=""></div>
    <div class="sim-note">Recognition is simulated in this prototype — it returns a prepared result for your
    nearest demo city rather than analysing your photo. A real build would send this image to a vision API.</div>
    <h2 style="font-size:23px;margin:4px 0 6px;letter-spacing:-.02em">${esc(lm.name)}</h2>
    <div class="detail-meta">${esc(lm.style)} · ${esc(lm.built)} · ${esc(CITIES[state.city].name)}</div>
    <div class="factgrid" style="margin-top:14px">
      <div class="fact"><div class="k">Built</div><div class="v">${esc(lm.built)}</div></div>
      <div class="fact"><div class="k">Style</div><div class="v" style="font-size:13px">${esc(lm.style)}</div></div>
    </div>
    <div class="section-title">The story</div>
    <p class="prose">${esc(lm.history)}</p>
    <div class="section-title">Also close by</div>
    <p class="prose">${lm.nearby.map(esc).join('<br>')}</p>
    <div class="section-title">Events connected to this</div>
    ${related.map(eventCard).join('')}
    <button class="btn secondary" id="againBtn">Scan something else</button>`;
  wireDiscoverResult();
}

function showTranslation(imgUrl) {
  const t = TRANSLATIONS[state.city];
  $('#discoverIntro').hidden = true;
  $('#discoverResult').hidden = false;
  $('#discoverResult').innerHTML = `
    <div class="camera-stage" style="aspect-ratio:16/10"><img src="${imgUrl}" alt=""></div>
    <div class="sim-note">Translation is simulated in this prototype — it returns a prepared result for
    ${esc(t.from)} rather than reading your photo. A real build would use a vision and translation API.</div>
    <div class="section-title">Detected · ${esc(t.from)}</div>
    <pre class="translated source">${esc(t.original)}</pre>
    <div class="section-title">English</div>
    <pre class="translated">${esc(t.translated)}</pre>
    <div class="banner"><strong>Good to know.</strong> ${esc(t.note)}</div>
    <button class="btn secondary" id="againBtn">Scan something else</button>`;
  wireDiscoverResult();
}

function wireDiscoverResult() {
  $('#againBtn').onclick = () => {
    $('#cameraStage').innerHTML = `<div class="camera-placeholder"><div class="big">◉</div>
      <div>Point your camera at a landmark, building, artwork or sign</div></div>`;
    renderDiscover();
  };
  $$('#discoverResult [data-event]').forEach((b) => b.onclick = () => showDetail(b.dataset.event));
}

/* ---------------- Plan a Trip ---------------- */

function hashDay(id, monthIdx, daysInMonth) {
  let h = monthIdx * 31;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return (h % daysInMonth) + 1;
}

function renderPlan() {
  const citySel = $('#planCity'), monthSel = $('#planMonth');
  if (!citySel.options.length) {
    citySel.innerHTML = Object.entries(CITIES).map(([k, c]) =>
      `<option value="${k}">${esc(c.name)}, ${esc(c.country)}</option>`).join('');
    citySel.value = state.city;
    const now = new Date().getMonth();
    monthSel.innerHTML = MONTHS.map((m, i) =>
      `<option value="${i}" ${i === now ? 'selected' : ''}>${m}</option>`).join('');
    citySel.onchange = monthSel.onchange = renderPlan;
  }

  const city = citySel.value, monthIdx = +monthSel.value;
  const year = new Date().getFullYear() + (monthIdx < new Date().getMonth() ? 1 : 0);
  const daysInMonth = new Date(year, monthIdx + 1, 0).getDate();
  const firstDow = (new Date(year, monthIdx, 1).getDay() + 6) % 7;

  const list = EVENTS.filter((e) => e.city === city)
    .map((e) => ({ ...e, planDay: hashDay(e.id, monthIdx, daysInMonth) }))
    .sort((a, b) => a.planDay - b.planDay);

  const byDay = {};
  list.forEach((e) => { (byDay[e.planDay] = byDay[e.planDay] || []).push(e); });

  let cal = '<div class="cal">' + ['M','T','W','T','F','S','S'].map((d) => `<div class="dow">${d}</div>`).join('');
  for (let i = 0; i < firstDow; i++) cal += '<div class="day blank"></div>';
  for (let d = 1; d <= daysInMonth; d++) {
    const n = byDay[d] ? byDay[d].length : 0;
    cal += `<div class="day ${n ? 'has' : ''}" ${n ? `data-n="${n}"` : ''}>${d}</div>`;
  }
  cal += '</div>';

  $('#planCal').innerHTML = `<div class="banner">Typical events for <strong>${esc(CITIES[city].name)}</strong>
    in <strong>${MONTHS[monthIdx]}</strong>. Dates are projected demo data — a real build would query live
    listings for the month you pick.</div>` + cal;

  $('#planList').innerHTML = list.map((e) => {
    const d = new Date(year, monthIdx, e.planDay);
    const cat = CATEGORIES[e.category];
    const p = fmtPrice(e);
    return `<button class="card" data-event="${esc(e.id)}">
      <div class="card-img" style="background:linear-gradient(135deg,${cat.c1},${cat.c2});height:96px">
        <span class="glyph" style="font-size:34px">${cat.icon}</span>
        <span class="cat">${esc(cat.label)}</span>
      </div>
      <div class="card-body">
        <h3>${esc(e.title)}</h3>
        <div class="card-meta">${esc(e.venue)}</div>
        <div class="card-foot">
          <span class="when">${d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })} · ${esc(e.time)}</span>
          <span class="price ${p.free ? 'free' : ''}">${esc(p.text)}</span>
        </div>
      </div>
    </button>`;
  }).join('');

  const it = $('#itinerary');
  it.innerHTML = state.itinerary.length ? state.itinerary.map((id) => {
    const ev = getEvent(id);
    if (!ev) return '';
    return `<div class="invite-row">
      <h4>${esc(ev.title)}</h4>
      <div class="who">${esc(ev.venue)} · ${esc(CITIES[ev.city].name)}</div>
      <div class="guest">
        <button data-event="${esc(ev.id)}" style="color:var(--accent);font-weight:700">View</button>
        <button data-drop="${esc(ev.id)}" style="color:var(--text-faint)">Remove</button>
      </div>
    </div>`;
  }).join('') : `<div class="empty"><div class="big">▤</div>Nothing saved yet.<br>Open an event and tap Add to itinerary.</div>`;

  $$('#screen-plan [data-event]').forEach((b) => b.onclick = () => showDetail(b.dataset.event));
  $$('[data-drop]').forEach((b) => b.onclick = () => {
    state.itinerary = state.itinerary.filter((x) => x !== b.dataset.drop);
    save(); renderPlan(); toast('Removed');
  });
}

/* ---------------- invite links ---------------- */

function handleHash() {
  const m = location.hash.match(/^#invite=([^&]+)&from=(.*)$/);
  if (!m) return false;
  const eventId = decodeURIComponent(m[1]);
  const from = decodeURIComponent(m[2]).slice(0, 60);
  history.replaceState(null, '', location.pathname);
  if (!getEvent(eventId)) return false;
  let inv = state.invitesIn.find((x) => x.eventId === eventId && x.from === from);
  if (!inv) {
    inv = { id: 'inv-' + Date.now(), eventId, from, status: 'pending' };
    state.invitesIn.unshift(inv);
    save();
  }
  showDetail(eventId, inv);
  return true;
}

/* ---------------- wiring ---------------- */

$$('.tabbar button').forEach((b) => b.onclick = () => go(b.dataset.tab));
$('#backBtn').onclick = () => go(state.tab === 'about' ? 'near' : 'near');
$('#aboutBtn').onclick = () => go('about');
$('#backdrop').onclick = closeSheet;

$('#dateFilter').onclick = (e) => {
  const b = e.target.closest('[data-when]'); if (!b) return;
  state.filters.when = b.dataset.when;
  $$('#dateFilter .chip').forEach((c) => c.classList.toggle('on', c === b));
  renderNear();
};
$('#priceFilter').onclick = (e) => {
  const b = e.target.closest('[data-max]'); if (!b) return;
  state.filters.max = +b.dataset.max;
  $$('#priceFilter .chip').forEach((c) => c.classList.toggle('on', c === b));
  renderNear();
};
$('#catFilter').innerHTML += Object.entries(CATEGORIES)
  .map(([k, c]) => `<button class="chip" data-cat="${k}">${c.icon} ${c.label}</button>`).join('');
$('#catFilter').onclick = (e) => {
  const b = e.target.closest('[data-cat]'); if (!b) return;
  state.filters.cat = b.dataset.cat;
  $$('#catFilter .chip').forEach((c) => c.classList.toggle('on', c === b));
  renderNear();
};
$$('.viewtoggle button').forEach((b) => b.onclick = () => {
  state.view = b.dataset.view;
  $$('.viewtoggle button').forEach((x) => x.classList.toggle('on', x === b));
  renderNear();
});
$('#nearList').onclick = (e) => {
  const b = e.target.closest('[data-event]'); if (b) showDetail(b.dataset.event);
};

$$('.modeswitch button').forEach((b) => b.onclick = () => {
  state.mode = b.dataset.mode;
  $$('.modeswitch button').forEach((x) => x.classList.toggle('on', x === b));
  $('#subtitle').textContent = defaultSub('discover');
  renderDiscover();
});
$('#startCamBtn').onclick = startCamera;
$('#shutterBtn').onclick = capture;
$('#fileInput').onchange = (e) => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => analyse(r.result);
  r.readAsDataURL(f);
};
$('#resetBtn').onclick = () => {
  try { localStorage.removeItem(STORE_KEY); localStorage.removeItem('touring-name'); } catch (e) {}
  location.reload();
};

window.addEventListener('hashchange', handleHash);

if (!handleHash()) go('near');
initLocation();
