// Uavert web map: talks only to /api/v1. All text from the API is inserted with textContent.
"use strict";

const BANDS = {
  lower: { label: "Lower reported risk", colour: "#f7e3a3" },
  moderate: { label: "Moderate risk", colour: "#f3a65a" },
  elevated: { label: "Elevated risk", colour: "#d9562f" },
  high: { label: "High risk", colour: "#9e1b2c" },
};
const CATEGORY_NAMES = { crime: "Crime", environment: "Air quality", alert: "Official alerts", news: "News" };
const SOURCE_NAMES = {};
const CELL_ZOOM = 14;

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const fmtDate = (iso) => {
  if (!iso) return "unknown";
  if (/^\d{4}$/.test(iso)) return iso;
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString("en-CA", { dateStyle: "medium", timeStyle: iso.length > 10 ? "short" : undefined });
};

async function api(path) {
  const r = await fetch(path);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error?.message || `Request failed (${r.status})`);
  return body;
}

function setStatus(text, isError = false) {
  $("status").textContent = text || "";
  $("status").className = "status" + (isError ? " error" : "");
}

// ---- map ---------------------------------------------------------------
const map = L.map("map", { zoomControl: true }).setView([43.7, -79.39], 11);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
map.attributionControl.addAttribution("Data: Toronto Police Service, Statistics Canada, Environment Canada");

const style = (band, fill = 0.55) => ({ color: "#fff", weight: 1, fillColor: BANDS[band].colour, fillOpacity: fill });
let hoodLayer, cellLayer, routeLayer, marker;

function renderLegend() {
  const legend = $("legend");
  Object.values(BANDS).forEach((b) => {
    const row = el("div"); const sw = el("i"); sw.style.background = b.colour;
    row.append(sw, document.createTextNode(b.label)); legend.append(row);
  });
}

async function loadNeighbourhoods() {
  const body = await api("/api/v1/neighbourhoods");
  hoodLayer = L.geoJSON(body.data, {
    style: (f) => style(f.properties.band),
    onEachFeature: (f, layer) => {
      layer.bindTooltip(`${f.properties.name}: ${f.properties.score}`, { sticky: true });
      layer.on("click", () => showNeighbourhood(f.properties.id));
    },
  }).addTo(map);
}

let cellTimer;
function scheduleCells() { clearTimeout(cellTimer); cellTimer = setTimeout(loadCells, 250); }

async function loadCells() {
  const show = map.getZoom() >= CELL_ZOOM;
  $("zoom-hint").hidden = show;
  if (hoodLayer) hoodLayer.setStyle((f) => style(f.properties.band, show ? 0.08 : 0.55));
  if (!show) { if (cellLayer) { map.removeLayer(cellLayer); cellLayer = null; } return; }
  const b = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((v) => v.toFixed(5)).join(",");
  try {
    const body = await api(`/api/v1/cells?bbox=${bbox}`);
    if (cellLayer) map.removeLayer(cellLayer);
    cellLayer = L.geoJSON(body.data, {
      style: (f) => style(f.properties.band, 0.6),
      onEachFeature: (f, layer) => {
        const p = f.properties;
        const around = p.vs_surroundings != null ? ` · ${timesAround(p.vs_surroundings)} its surroundings` : "";
        layer.bindTooltip(`Street score ${p.score}${around} · ${peoplePerHour(p.foot_traffic_per_hour)}`, { sticky: true });
        layer.on("click", (e) => checkPoint(e.latlng.lat, e.latlng.lng));
      },
    }).addTo(map);
    if (routeLayer) routeLayer.bringToFront();
  } catch (e) { setStatus(e.message, true); }
}
map.on("moveend", scheduleCells);

// ---- details panel -----------------------------------------------------
function showScore(title, sub, score, extraNodes = []) {
  $("details").hidden = false;
  const badge = $("score-badge");
  badge.textContent = score.score;
  badge.className = `score-badge b-${score.band}`;
  $("score-band").textContent = BANDS[score.band].label;
  $("score-title").textContent = title;
  $("score-sub").textContent = sub || "";

  const cats = $("cats"); cats.replaceChildren();
  Object.entries(score.categories).forEach(([k, v]) => {
    const row = el("div", "cat"); const bar = el("div", "bar"); const fill = el("i");
    fill.style.width = `${v}%`; fill.style.background = BANDS[bandFor(v)].colour; bar.append(fill);
    row.append(el("span", null, CATEGORY_NAMES[k] || k), bar, el("b", null, String(v))); cats.append(row);
  });

  const list = $("reasons"); list.replaceChildren();
  (score.reasons || []).forEach((r) => list.append(reasonItem(r)));
  if (!score.reasons?.length) list.append(el("li", "muted", "No specific reasons recorded."));
  $("extra").replaceChildren(...extraNodes);
  $("details").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function reasonItem(r) {
  const li = el("li");
  if (r.url) { const a = el("a", null, r.text); a.href = r.url; a.target = "_blank"; a.rel = "noopener"; li.append(a); }
  else li.append(document.createTextNode(r.text));
  li.append(el("span", "meta", `${SOURCE_NAMES[r.source_key] || r.source_key} · data ${fmtDate(r.as_of)} · collected ${fmtDate(r.collected_at)}`));
  return li;
}

const timesAround = (r) => (r == null ? null : r > 10 ? "more than 10×" : `${r.toFixed(1)}×`);
const peoplePerHour = (n) => (n == null ? "unknown" : `about ${Math.round(n).toLocaleString("en-CA")} people an hour on foot`);

const bandFor = (s) => (s >= 75 ? "high" : s >= 50 ? "elevated" : s >= 25 ? "moderate" : "lower");

async function showNeighbourhood(id) {
  try {
    const d = (await api(`/api/v1/neighbourhoods/${id}`)).data;
    showScore(d.name, `Neighbourhood · population ${d.population?.toLocaleString("en-CA") ?? "n/a"} (${d.population_year})`, d);
  } catch (e) { setStatus(e.message, true); }
}

async function checkPoint(lat, lon) {
  await runDestination(`/api/v1/risk-scores?lat=${lat.toFixed(6)}&lon=${lon.toFixed(6)}`, null);
}

async function runDestination(path, label) {
  setStatus("Checking...");
  try {
    const d = (await api(path)).data;
    setStatus("");
    if (marker) map.removeLayer(marker);
    marker = L.marker([d.location.lat, d.location.lon]).addTo(map);
    if (label) map.setView([d.location.lat, d.location.lon], 15);
    const hood = el("p", "muted",
      `Neighbourhood: ${d.neighbourhood.name} - ${d.neighbourhood.score} (${BANDS[d.neighbourhood.band].label.toLowerCase()})`);
    const s = d.street;
    const where = s.incident_count != null
      ? `Street level (about one block) · ${s.incident_count} street incidents within ~250 m · ${peoplePerHour(s.foot_traffic_per_hour)}`
        + (s.vs_surroundings != null ? ` · ${timesAround(s.vs_surroundings)} the reported street crime of the surrounding 1 km, per person` : "")
      : "Street level unavailable here; showing the neighbourhood";
    showScore(label || d.location.display_name.split(",").slice(0, 3).join(","), where, d.street, [hood]);
  } catch (e) { setStatus(e.message, true); }
}

$("dest-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $("dest").value.trim();
  runDestination(`/api/v1/risk-scores?address=${encodeURIComponent(q)}`, q);
});

$("route-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter; btn.disabled = true;
  setStatus("Finding a walking route...");
  try {
    const from = $("from").value.trim(), to = $("to").value.trim();
    const d = (await api(`/api/v1/route-risks?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`)).data;
    setStatus("");
    if (routeLayer) map.removeLayer(routeLayer);
    routeLayer = L.layerGroup().addTo(map);
    const line = L.geoJSON(d.geometry, { style: { color: "#1f4e79", weight: 5, opacity: 0.85 } }).addTo(routeLayer);
    d.riskiest_segments.forEach((s, i) => L.geoJSON(s.geometry, { style: { color: BANDS[s.band].colour, weight: 9, opacity: 0.95 } })
      .bindTooltip(`Stands out ${i + 1}: ${timesAround(s.vs_surroundings)} its surroundings`).addTo(routeLayer));
    map.fitBounds(line.getBounds(), { padding: [30, 30] });

    const segs = el("ol", "reasons segments");
    d.riskiest_segments.forEach((s) => {
      const li = el("li", null, `${timesAround(s.vs_surroundings)} the reported street crime of its surroundings, per person · ${s.length_m} m · score ${s.score}`);
      li.append(el("span", "meta", `${peoplePerHour(s.foot_traffic_per_hour)}${s.reasons[0] ? " · " + s.reasons[0].text : ""}`));
      segs.append(li);
    });
    const title = el("h3", null, "Stretches that stand out");
    const mins = Math.round(d.duration_s / 60);
    showScore(`${d.from.display_name.split(",")[0]} → ${d.to.display_name.split(",")[0]}`,
      `Walking route · ${(d.distance_m / 1000).toFixed(1)} km · about ${mins} min · highest score along the way`, d,
      d.riskiest_segments.length ? [title, segs] : [title, el("p", "muted", d.segments_note)]);
  } catch (err) { setStatus(err.message, true); }
  finally { btn.disabled = false; }
});

// ---- news and sources --------------------------------------------------
async function loadNews() {
  const list = $("news");
  try {
    const items = (await api("/api/v1/news-events?since_hours=24")).data;
    list.replaceChildren();
    if (!items.length) list.append(el("li", "muted", "No protest or violent-incident reports in Toronto news in the last 24 hours."));
    items.forEach((n) => {
      const li = el("li"); const a = el("a", null, n.headline); a.href = n.url; a.target = "_blank"; a.rel = "noopener";
      li.append(a, el("span", "meta", `${n.category === "protest" ? "Protest" : "Violent incident"} · ${n.citywide ? "location unknown (not scored)" : n.location_text} · ${n.publisher} · ${fmtDate(n.published_at)}`));
      list.append(li);
    });
  } catch (e) { list.replaceChildren(el("li", "muted", e.message)); }
}

async function loadSources() {
  const list = $("sources");
  try {
    const items = (await api("/api/v1/sources")).data;
    list.replaceChildren();
    items.forEach((s) => {
      SOURCE_NAMES[s.key] = s.name;
      const li = el("li", null, s.name);
      let text;
      if (!s.collected_at) text = s.last_status === "failed" ? "not collected yet: the service didn't respond" : "not collected yet";
      else {
        text = `${s.as_of ? `data up to ${fmtDate(s.as_of)}` : "nothing current"} · collected ${fmtDate(s.collected_at)}`;
        if (s.last_status === "failed") text += " · latest attempt failed, showing earlier data";
      }
      li.append(el("span", "meta" + (s.last_status === "failed" ? " failed" : ""), text));
      list.append(li);
    });
  } catch (e) { list.replaceChildren(el("li", "muted", e.message)); }
}

renderLegend();
loadSources().then(() => Promise.all([loadNeighbourhoods(), loadNews()])).then(loadCells)
  .catch((e) => setStatus(e.message, true));
