// Uavert web map: talks only to /api/v1. All text from the API is inserted with textContent.
"use strict";

const BANDS = {
  lower: { label: "Lower reported risk", colour: "#2e9e57" },
  moderate: { label: "Moderate risk", colour: "#f2c230" },
  elevated: { label: "Elevated risk", colour: "#e8792b" },
  high: { label: "High risk", colour: "#c62828" },
};
const CATEGORY_NAMES = { crime: "Crime", environment: "Air quality", alert: "Official alerts", news: "News", crowds: "Crowds" };
const SOURCE_NAMES = {};
const SOURCE_DATES = {}; // source key -> the newest date its data refers to
const CELL_ZOOM = 14;
const TZ = "America/Toronto";

// ---- time of day ---------------------------------------------------------
const hourLabel = (h) => `${h % 12 || 12} ${h < 12 ? "am" : "pm"}`;
const torontoHour = () => Number(new Intl.DateTimeFormat("en-CA", { hour: "numeric", hourCycle: "h23", timeZone: TZ }).format(new Date()));
let lastSearch = null; // re-run when the time changes

function selectedHour() {
  const v = document.getElementById("when").value;
  return v === "all" ? null : v === "now" ? torontoHour() : Number(v);
}
const hourParam = () => { const h = selectedHour(); return h == null ? "" : `&hour=${h}`; };
const timeText = () => { const h = selectedHour(); return h == null ? "All day" : hourLabel(h); };

function fillTimeSelector() {
  const sel = document.getElementById("when");
  const opt = (value, text) => { const o = document.createElement("option"); o.value = value; o.textContent = text; sel.append(o); };
  opt("all", "All day");
  opt("now", `Now (${hourLabel(torontoHour())})`);
  for (let h = 0; h < 24; h++) opt(String(h), hourLabel(h));
}

const $ = (id) => document.getElementById(id);
// Links come from outside feeds: only ordinary web links are clickable.
const safeUrl = (u) => { try { const p = new URL(u); return p.protocol === "https:" || p.protocol === "http:" ? p.href : null; } catch { return null; } };
// Leaflet tooltips render HTML, so text from data is escaped first.
const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const fmtDate = (iso) => {
  if (!iso) return "unknown";
  if (/^\d{4}$/.test(iso)) return iso;
  // Whole-day dates are stored as midnight UTC; show the date itself, not the local time it converts to.
  const day = iso.match(/^(\d{4}-\d{2}-\d{2})(T00:00:00(\.0+)?(\+00:00|Z))?$/);
  if (day) return new Date(`${day[1]}T12:00:00`).toLocaleDateString("en-CA", { dateStyle: "medium" });
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

const hoodFill = () => (map.getZoom() >= CELL_ZOOM ? 0.08 : 0.55);
const hoodTooltip = (p) => {
  const h = selectedHour();
  return `${escapeHtml(p.name)}: ${p.score}${h == null ? "" : ` at ${hourLabel(h)}`}`;
};
let hoodRequest = 0;

// Neighbourhood colours follow the "When" setting (01-03-time-map.md): the first load draws the layer,
// later loads re-colour it in place.
async function loadNeighbourhoods() {
  const request = ++hoodRequest;
  const body = await api(`/api/v1/neighbourhoods?${hourParam().slice(1)}`);
  if (request !== hoodRequest) return; // the time changed while this was loading
  if (!hoodLayer) {
    hoodLayer = L.geoJSON(body.data, {
      style: (f) => style(f.properties.band, hoodFill()),
      onEachFeature: (f, layer) => {
        layer.bindTooltip(hoodTooltip(f.properties), { sticky: true });
        layer.on("click", () => showNeighbourhood(f.properties.id));
      },
    }).addTo(map);
    return;
  }
  const byId = new Map(body.data.features.map((f) => [f.properties.id, f.properties]));
  hoodLayer.eachLayer((layer) => {
    const p = byId.get(layer.feature.properties.id);
    if (!p) return;
    layer.feature.properties = p;
    layer.setTooltipContent(hoodTooltip(p));
  });
  hoodLayer.setStyle((f) => style(f.properties.band, hoodFill()));
}

let cellTimer, cellRequest = 0;
function scheduleCells() { clearTimeout(cellTimer); cellTimer = setTimeout(loadCells, 250); }

async function loadCells() {
  const request = ++cellRequest;
  const show = map.getZoom() >= CELL_ZOOM;
  $("zoom-hint").hidden = show;
  if (hoodLayer) hoodLayer.setStyle((f) => style(f.properties.band, hoodFill()));
  if (!show) { if (cellLayer) { map.removeLayer(cellLayer); cellLayer = null; } return; }
  const b = map.getBounds();
  const bbox = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map((v) => v.toFixed(5)).join(",");
  try {
    const body = await api(`/api/v1/cells?bbox=${bbox}${hourParam()}`);
    if (request !== cellRequest) return; // the view or the time changed while this was loading
    if (cellLayer) map.removeLayer(cellLayer);
    cellLayer = L.geoJSON(body.data, {
      style: (f) => style(f.properties.band, 0.6),
      onEachFeature: (f, layer) => {
        const p = f.properties;
        const around = p.vs_surroundings != null ? ` · ${timesAround(p.vs_surroundings)} its surroundings` : "";
        layer.bindTooltip(escapeHtml(`Street score ${p.score}${around} · ${peoplePerHour(p.foot_traffic_per_hour)}`), { sticky: true });
        layer.on("click", (e) => checkPoint(e.latlng.lat, e.latlng.lng));
      },
    }).addTo(map);
    if (routeLayer) routeLayer.bringToFront();
  } catch (e) { setStatus(e.message, true); }
}
map.on("moveend", scheduleCells);

// ---- risk score gauge (01-03-gauge.md) -------------------------------------
// A half-circle dial, 0 on the left to 100 on the right, in the map's band colours; the needle points at the score.
const GAUGE = { cx: 66, cy: 70, r: 54, width: 12 };
const BAND_RANGES = [["lower", 0, 25], ["moderate", 25, 50], ["elevated", 50, 75], ["high", 75, 100]]; // as bandFor
const gaugePoint = (s, r = GAUGE.r) => {
  const a = Math.PI * (1 - s / 100);
  return [GAUGE.cx + r * Math.cos(a), GAUGE.cy - r * Math.sin(a)].map((v) => v.toFixed(2)).join(" ");
};

function gaugeSvg() {
  const svg = svgEl("svg", { viewBox: "0 0 132 80", width: 132, height: 80, "aria-hidden": "true", class: "gauge-dial" });
  BAND_RANGES.forEach(([band, from, to]) => {
    // a hair of space between sections, none at the ends
    const a = from === 0 ? 0 : from + 0.6, b = to === 100 ? 100 : to - 0.6;
    svg.append(svgEl("path", { d: `M ${gaugePoint(a)} A ${GAUGE.r} ${GAUGE.r} 0 0 1 ${gaugePoint(b)}`, fill: "none",
      stroke: BANDS[band].colour, "stroke-width": GAUGE.width, "data-band": band }));
  });
  [0, 25, 50, 75, 100].forEach((s) => svg.append(svgEl("path", {
    d: `M ${gaugePoint(s, GAUGE.r - GAUGE.width / 2 - 2)} L ${gaugePoint(s, GAUGE.r - GAUGE.width / 2 - 7)}`, class: "gauge-tick" })));
  // drawn pointing at 0 (left); turned to the score with a CSS rotation so it can swing
  svg.append(svgEl("line", { x1: GAUGE.cx, y1: GAUGE.cy, x2: GAUGE.cx - (GAUGE.r - 10), y2: GAUGE.cy, class: "gauge-needle" }),
    svgEl("circle", { cx: GAUGE.cx, cy: GAUGE.cy, r: 5, class: "gauge-hub" }),
    // a walk's worst block: a small triangle just outside the arc, pointing in (01-03-panel-tidy.md)
    svgEl("path", { d: "M -5.5 -4.5 L 5.5 -4.5 L 0 4.5 Z", class: "gauge-worst", hidden: "" }));
  return svg;
}

function placeWorst(marker, worst) {
  if (!worst) { marker.setAttribute("hidden", ""); return; }
  const s = Math.max(0, Math.min(100, worst.score));
  marker.removeAttribute("hidden");
  marker.setAttribute("fill", BANDS[worst.band].colour);
  marker.setAttribute("transform", `translate(${gaugePoint(s, GAUGE.r + GAUGE.width / 2 + 5).replace(" ", ",")}) rotate(${(s - 50) * 1.8})`);
}

function setGauge(score, band, worst = null) {
  const box = $("score-badge");
  if (!box.querySelector("svg")) {
    box.replaceChildren(gaugeSvg(), el("span", "gauge-num"));
    box.className = "gauge";
    box.setAttribute("role", "img");
  }
  box.querySelector(".gauge-num").textContent = score;
  box.setAttribute("aria-label", `Risk score ${score} out of 100: ${BANDS[band].label.toLowerCase()}`
    + (worst ? `, worst block ${worst.score}: ${BANDS[worst.band].label.toLowerCase()}` : ""));
  placeWorst(box.querySelector(".gauge-worst"), worst);
  const needle = box.querySelector(".gauge-needle");
  requestAnimationFrame(() => { needle.style.transform = `rotate(${(Math.max(0, Math.min(100, score)) / 100) * 180}deg)`; });
}

// ---- details panel -----------------------------------------------------
// `worst`: for a walk, its worst block, marked on the dial and named under the title (01-03-panel-tidy.md).
function showScore(title, sub, score, extraNodes = [], oddsNodes = [], trendNodes = [], worst = null) {
  $("details").hidden = false;
  const markWorst = worst && worst.score !== score.score ? worst : null;
  setGauge(score.score, score.band, markWorst);
  $("score-band").textContent = BANDS[score.band].label;
  $("score-title").textContent = title;
  $("score-worst").hidden = !worst;
  $("score-worst").textContent = worst
    ? `Worst block: ${worst.score} (${BANDS[worst.band].label.toLowerCase()}) · highlighted on the map` : "";
  $("score-sub").textContent = sub || "";
  $("odds").replaceChildren(...oddsNodes); // directly under the score (01-03-odds.md)
  $("trend").replaceChildren(...trendNodes); // under the odds (01-03-trends.md)

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
  const href = r.url && safeUrl(r.url);
  if (href) { const a = el("a", null, r.text); a.href = href; a.target = "_blank"; a.rel = "noopener"; li.append(a); }
  else li.append(document.createTextNode(r.text));
  li.append(el("span", "meta", `${SOURCE_NAMES[r.source_key] || r.source_key} · data ${fmtDate(r.as_of)} · collected ${fmtDate(r.collected_at)}`));
  return li;
}

const timesAround = (r) => (r == null ? null : r > 10 ? "more than 10×" : `${r.toFixed(1)}×`);
const peoplePerHour = (n) => (n == null ? "unknown" : `about ${Math.round(n).toLocaleString("en-CA")} people an hour on foot`);

// ---- odds per resident (01-03-odds.md) -----------------------------------
const ODDS_LEVELS = [["high", "High: serious violence"], ["medium", "Medium: assault"], ["low", "Low: property crime"], ["any", "Any"]];
const oneIn = (n) => (n == null ? "None reported" : `1 in ${n.toLocaleString("en-CA")}`);
// incidents as a share of residents, two significant figures (01-03-odds-percent.md)
const pct = (incidents, population) => `${Number((100 * incidents / population).toPrecision(2))}%`;
const oddsCell = (n, incidents, population) => (n == null ? oneIn(n) : `${oneIn(n)} (${pct(incidents, population)})`);

function oddsNodes(odds, name) {
  if (!odds) return [];
  const table = el("table", "odds");
  const head = el("tr");
  head.append(...["Severity", "Here", "Toronto"].map((t) => Object.assign(el("th", null, t), { scope: "col" })));
  table.append(head);
  ODDS_LEVELS.forEach(([k, label]) => {
    const l = odds.levels[k]; const row = el("tr");
    row.append(Object.assign(el("th", null, label), { scope: "row" }), el("td", null, oddsCell(l.one_in, l.incidents, odds.population)),
      el("td", null, oddsCell(l.toronto_one_in, l.toronto_incidents, odds.toronto_population)));
    table.append(row);
  });
  const note = el("p", "meta", "One reported incident a year for every N residents (P% of the population). Not a personal prediction: many incidents involve visitors, "
    + "some aren't reported, and property crimes affect cars and homes rather than people. ");
  const how = el("a", null, "How this is worked out"); how.href = "/rules.html#odds"; note.append(how);
  return [el("h3", null, `Odds in ${name} (${odds.year}), per resident (yearly)`), table, note];
}

// ---- crime trends (01-03-trends.md) ------------------------------------------
const TREND_GROUPS = [["violent", "Violent"], ["property", "Property"], ["all", "All"]];
const TREND_WINDOWS = [["10", "10 years"], ["5", "5 years"]];
const OFFENCE_NAMES = { ASSAULT: "Assaults", ROBBERY: "Robberies", HOMICIDE: "Homicides", SHOOTING: "Shootings",
  BREAKENTER: "Break-ins", AUTOTHEFT: "Auto thefts", THEFTOVER: "Thefts over $5,000", THEFTFROMMV: "Thefts from vehicles",
  BIKETHEFT: "Bicycle thefts" };
const trendView = { window: "10", group: "violent" }; // kept between places
const svgEl = (tag, attrs) => {
  const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
  return e;
};
const signedPct = (n) => `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n)}%`;

function trendWords(s) {
  if (s.direction === "too_few") return "too few to call a trend";
  return `${{ rising: "rising", falling: "falling", flat: "roughly flat" }[s.direction]}, ${signedPct(s.change_pct)}`;
}

// The least-squares line through the points, as drawn: the same fit the server uses for the % change.
function fitted(values) {
  const n = values.length, mx = (n - 1) / 2, my = values.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  values.forEach((v, x) => { num += (x - mx) * (v - my); den += (x - mx) ** 2; });
  return [my - (num / den) * mx, my + (num / den) * mx];
}

function trendChart(here, toronto, label) {
  const W = 320, H = 150, L = 34, R = 8, T = 8, B = 20;
  const top = Math.max(...here.map((p) => p.rate_per_1000), ...toronto.map((p) => p.rate_per_1000)) * 1.1 || 1;
  const x = (i) => L + (i * (W - L - R)) / (here.length - 1);
  const y = (v) => T + (H - T - B) * (1 - v / top);
  const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "trend-chart", role: "img", "aria-label": label });
  [0, top / 2, top].forEach((v) => {
    svg.append(svgEl("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "t-grid" }));
    const t = svgEl("text", { x: L - 4, y: y(v) + 3, class: "t-axis", "text-anchor": "end" });
    t.textContent = v.toFixed(top < 10 ? 1 : 0); svg.append(t);
  });
  [0, here.length - 1].forEach((i) => {
    const t = svgEl("text", { x: x(i), y: H - 5, class: "t-axis", "text-anchor": i ? "end" : "start" });
    t.textContent = here[i].year; svg.append(t);
  });
  const line = (pts, cls) => svg.append(svgEl("polyline", { points: pts.map((p, i) => `${x(i)},${y(p.rate_per_1000)}`).join(" "), class: cls }));
  line(toronto, "t-toronto");
  line(here, "t-here");
  const [a, b] = fitted(here.map((p) => p.rate_per_1000));
  svg.append(svgEl("line", { x1: x(0), y1: y(a), x2: x(here.length - 1), y2: y(b), class: "t-fit" }));
  here.forEach((p, i) => svg.append(svgEl("circle", { cx: x(i), cy: y(p.rate_per_1000), r: 2.5, class: "t-dot" })));
  return svg;
}

function segmented(options, current, label, onPick) {
  const box = el("div", "seg"); box.setAttribute("role", "group"); box.setAttribute("aria-label", label);
  options.forEach(([k, text]) => {
    const btn = el("button", null, text); btn.type = "button"; btn.dataset.key = `${label}:${k}`;
    btn.setAttribute("aria-pressed", String(k === current));
    btn.addEventListener("click", () => onPick(k, btn.dataset.key));
    box.append(btn);
  });
  return box;
}

function figuresTable(headings, rows) {
  const table = el("table", "odds");
  const head = el("tr"); head.append(...headings.map((t) => Object.assign(el("th", null, t), { scope: "col" })));
  table.append(head);
  rows.forEach(([first, ...cells]) => {
    const row = el("tr");
    row.append(Object.assign(el("th", null, first), { scope: "row" }), ...cells.map((c) => el("td", null, c)));
    table.append(row);
  });
  return table;
}

function trendNodes(trend, name) {
  if (!trend) return [];
  const wrap = el("div", "trend");
  const render = (focusKey) => {
    const w = trend.windows[trendView.window], tw = trend.toronto.windows[trendView.window];
    const cut = (pts) => pts.filter((p) => p.year >= w.first_year);
    const here = cut(trend.series[trendView.group]), toronto = cut(trend.toronto.series[trendView.group]);
    const years = `${w.first_year}–${w.last_year}`;

    const controls = el("div", "trend-controls");
    controls.append(
      segmented(TREND_WINDOWS, trendView.window, "Period", (k, key) => { trendView.window = k; render(key); }),
      segmented(TREND_GROUPS, trendView.group, "Crime type", (k, key) => { trendView.group = k; render(key); }));

    const legend = el("div", "trend-legend");
    [["t-key-here", name], ["t-key-fit", "Trendline"], ["t-key-toronto", "Toronto"]].forEach(([cls, text]) => {
      const item = el("span"); item.append(el("i", cls), document.createTextNode(text)); legend.append(item);
    });

    const summary = el("ul", "trend-summary");
    [["violent", "Violent crime"], ["property", "Property crime"]].forEach(([g, label]) => {
      const li = el("li");
      li.append(el("b", null, `${label}: `),
        document.createTextNode(`${trendWords(w.groups[g])} over ${years} (Toronto: ${trendWords(tw.groups[g])})`));
      summary.append(li);
    });

    const byOffence = el("details");
    byOffence.append(el("summary", null, "By offence"), figuresTable(["Offence", String(w.last_year), `Trend ${years}`],
      Object.entries(w.offences).map(([k, s]) => [OFFENCE_NAMES[k] || k, s.count_last_year.toLocaleString("en-CA"), trendWords(s)])));

    const yearly = el("details");
    yearly.append(el("summary", null, "Yearly figures"),
      el("p", "meta", "Reported incidents per 1,000 residents (count in brackets)."),
      figuresTable(["Year", name, "Toronto"], here.map((p, i) => [String(p.year),
        `${p.rate_per_1000.toFixed(1)} (${p.count.toLocaleString("en-CA")})`, toronto[i].rate_per_1000.toFixed(1)])));

    const note = el("p", "meta", "Per resident, so places with many visitors look higher. Reported incidents only. "
      + "2020 and 2021 were pandemic years with less activity. Source: Toronto Police Service, Neighbourhood Crime Rates. ");
    const how = el("a", null, "How this is worked out"); how.href = "/rules.html#trends"; note.append(how);

    const groupName = TREND_GROUPS.find(([k]) => k === trendView.group)[1];
    const chartLabel = `${groupName} crime per 1,000 residents in ${name}, ${years}: ${trendWords(w.groups[trendView.group])}; `
      + `Toronto ${trendWords(tw.groups[trendView.group])}. The yearly figures are in the table below.`;
    wrap.replaceChildren(el("h3", null, `Trend in ${name}, per 1,000 residents (yearly)`), controls,
      trendChart(here, toronto, chartLabel), legend, summary, byOffence, yearly, note);
    if (focusKey) wrap.querySelector(`[data-key="${focusKey}"]`)?.focus();
  };
  render();
  return [wrap];
}

const bandFor = (s) => (s >= 75 ? "high" : s >= 50 ? "elevated" : s >= 25 ? "moderate" : "lower");

async function showNeighbourhood(id) {
  lastSearch = () => showNeighbourhood(id);
  try {
    const d = (await api(`/api/v1/neighbourhoods/${id}?${hourParam().slice(1)}`)).data;
    showScore(d.name, `Showing: ${timeText()} · Neighbourhood · population ${d.population?.toLocaleString("en-CA") ?? "n/a"} (${d.population_year})`, d,
      patternNodes(d.patterns), oddsNodes(d.odds, d.name), trendNodes(d.trend, d.name));
  } catch (e) { setStatus(e.message, true); }
}

async function checkPoint(lat, lon) {
  await runDestination(`/api/v1/risk-scores?lat=${lat.toFixed(6)}&lon=${lon.toFixed(6)}`);
}

// A clicked street cell; "Where I'm going" was removed (01-03-time-map.md).
async function runDestination(path) {
  lastSearch = () => runDestination(path);
  setStatus("Checking...");
  try {
    const d = (await api(path + hourParam())).data;
    setStatus("");
    if (marker) map.removeLayer(marker);
    marker = L.marker([d.location.lat, d.location.lon]).addTo(map);
    const hood = el("p", "muted",
      `Neighbourhood: ${d.neighbourhood.name} - ${d.neighbourhood.score} (${BANDS[d.neighbourhood.band].label.toLowerCase()})`);
    const s = d.street;
    const where = s.incident_count != null
      ? `Street level (about one block) · ${s.incident_count} street incidents within ~250 m · ${peoplePerHour(s.foot_traffic_per_hour)}`
        + (s.vs_surroundings != null ? ` · ${timesAround(s.vs_surroundings)} the reported street crime of the surrounding 1 km, per person` : "")
      : "Street level unavailable here; showing the neighbourhood";
    showScore(d.location.display_name.split(",").slice(0, 3).join(","), `Showing: ${timeText()} · ${where}`, d.street,
      [hood], oddsNodes(d.neighbourhood.odds, d.neighbourhood.name), trendNodes(d.neighbourhood.trend, d.neighbourhood.name));
  } catch (e) { setStatus(e.message, true); }
}

$("route-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const from = $("from").value.trim(), to = $("to").value.trim();
  runRoute(from, to, e.submitter);
});

async function runRoute(from, to, btn) {
  lastSearch = () => runRoute(from, to, null);
  if (btn) btn.disabled = true;
  setStatus("Finding a walking route...");
  try {
    const d = (await api(`/api/v1/route-risks?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}${hourParam()}`)).data;
    setStatus("");
    if (routeLayer) map.removeLayer(routeLayer);
    routeLayer = L.featureGroup().addTo(map); // a featureGroup, so loadCells can bring the walk to the front
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
    // The headline is the walk's typical block; the worst block stays on the dial, under the title, on the map
    // and with its own reasons (01-03-panel-tidy.md).
    const headline = d.typical || d;
    const worstReasons = el("ul", "reasons");
    (d.reasons || []).forEach((r) => worstReasons.append(reasonItem(r)));
    showScore(`${d.from.display_name.split(",")[0]} → ${d.to.display_name.split(",")[0]}`,
      `Showing: ${timeText()} · Walking route · ${(d.distance_m / 1000).toFixed(1)} km · about ${mins} min · `
        + (d.typical ? "typical block along the walk" : "worst block shown"), headline,
      [el("h3", null, "Worst block"), worstReasons, title,
        ...(d.riskiest_segments.length ? [segs] : [el("p", "muted", d.segments_note)])],
      [], [], d.typical ? { score: d.score, band: d.band } : null);
  } catch (err) { setStatus(err.message, true); }
  finally { if (btn) btn.disabled = false; }
}

$("when").addEventListener("change", () => {
  loadNeighbourhoods().catch((e) => setStatus(e.message, true));
  loadCells();
  if (lastSearch) lastSearch();
});

// ---- news and sources --------------------------------------------------
// News by type of event, trending stories and patterns in police reports (01-03-news.md).
const NEWS_TYPES = [["protest", "Protests", "Protest"], ["violent_incident", "Violent incidents", "Violent incident"],
  ["property_crime", "Property crime", "Property crime"]];
const headlineLink = (text, url) => {
  const href = safeUrl(url);
  return href ? Object.assign(el("a", null, text), { href, target: "_blank", rel: "noopener" }) : el("span", null, text);
};
const where = (n) => (n.category === "property_crime" ? (n.location_text || "location unknown")
  : n.citywide ? "location unknown (not scored)" : n.location_text);

// Each part of "News and patterns" is its own dropdown, closed until opened (01-03-panel-tidy.md).
function newsSection(name, count, ...body) {
  const d = el("details", "news-section");
  d.append(el("summary", null, `${name} (${count})`), ...body);
  return d;
}
const unverified = (text) => { const p = el("p", "meta"); p.append(el("span", "tag", "unverified"), document.createTextNode(` ${text}`)); return p; };

function newsList(items, days) {
  const list = el("ul", "news");
  if (!items.length) list.append(el("li", "muted", `None in Toronto news in the last ${days} days.`));
  items.forEach((n) => {
    const li = el("li");
    li.append(headlineLink(n.headline, n.url), el("span", "meta", `${where(n)} · ${n.publisher} · ${fmtDate(n.published_at)}`));
    list.append(li);
  });
  return list;
}

function trendingItem(t) {
  const li = el("li");
  const type = NEWS_TYPES.find(([k]) => k === t.category)?.[2] || t.category;
  li.append(headlineLink(t.headline, t.url),
    el("span", "meta", `${type} · ${t.story_count} stories from ${t.outlet_count} outlets since ${fmtDate(t.first_published_at)}`));
  const all = el("details");
  const list = el("ul", "news");
  t.stories.forEach((s) => {
    const item = el("li"); item.append(headlineLink(s.headline, s.url), el("span", "meta", `${s.publisher} · ${fmtDate(s.published_at)}`));
    list.append(item);
  });
  all.append(el("summary", null, `All ${t.story_count} stories`), list);
  li.append(all);
  return li;
}

const patternText = (p) => `${p.recent} ${p.offence_label} reported in ${p.neighbourhood} between ${fmtDate(p.first_date)} and `
  + `${fmtDate(p.last_date)}, about ${p.times_usual}× the usual for this area`;

async function loadNews() {
  const [news, trending, patterns] = await Promise.allSettled([
    api("/api/v1/news-events?window=by_type&limit=100"), api("/api/v1/news-trending"), api("/api/v1/crime-patterns")]);

  const sections = [];
  if (trending.status === "fulfilled") {
    const groups = trending.value.data;
    const list = el("ul", "news");
    list.append(...groups.map(trendingItem));
    if (!groups.length) list.append(el("li", "muted", "No story is being covered by several outlets right now."));
    sections.push(newsSection("Trending", groups.length, unverified("Stories several outlets are covering, last 3 days."), list));
  } else sections.push(newsSection("Trending", "unavailable", el("p", "muted", trending.reason.message)));

  NEWS_TYPES.forEach(([k, label]) => {
    const days = { protest: 2, violent_incident: 7, property_crime: 60 }[k];
    if (news.status !== "fulfilled") {
      sections.push(newsSection(`${label} · last ${days} days`, "unavailable", el("p", "muted", news.reason.message)));
      return;
    }
    const mine = news.value.data.filter((n) => n.category === k);
    sections.push(newsSection(`${label} · last ${days} days`, mine.length, unverified("From Toronto news; matched by keywords."), newsList(mine, days)));
  });

  if (patterns.status === "fulfilled") {
    const found = patterns.value.data;
    const list = el("ul", "news");
    list.append(...found.map((p) => {
      const li = el("li"); const open = el("button", "linkish", patternText(p));
      open.type = "button";
      open.addEventListener("click", () => showNeighbourhood(p.neighbourhood_id));
      li.append(open); return li;
    }));
    if (!found.length) list.append(el("li", "muted", "No unusual break-in or auto-theft patterns in the latest 30 days of police data."));
    const asOf = found[0]?.data_as_of || SOURCE_DATES.tps_mci;
    const note = el("p", "meta", `Toronto Police data${asOf ? ` up to ${fmtDate(asOf)}` : ""}: neighbourhoods with at least `
      + "5 reports in their latest 30 days, at least twice their usual, and unlikely to be chance. Reported incidents only; not a prediction.");
    sections.push(newsSection("Patterns in police reports", found.length, list, note));
  } else sections.push(newsSection("Patterns in police reports", "unavailable", el("p", "muted", patterns.reason.message)));

  $("news-sections").replaceChildren(...sections);
}

function patternNodes(found) {
  if (!found?.length) return [];
  return [el("h3", null, "Pattern in police reports"), ...found.map((p) => el("p", "muted", patternText(p)))];
}

async function loadSources() {
  const list = $("sources");
  try {
    const items = (await api("/api/v1/sources")).data;
    list.replaceChildren();
    items.forEach((s) => {
      SOURCE_NAMES[s.key] = s.name;
      SOURCE_DATES[s.key] = s.as_of;
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

fillTimeSelector();
renderLegend();
loadSources().then(() => Promise.all([loadNeighbourhoods(), loadNews()])).then(loadCells)
  .catch((e) => setStatus(e.message, true));
