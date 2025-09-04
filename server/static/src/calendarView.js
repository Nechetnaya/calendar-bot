// calendarView.js — month: dots, week/day: full visible events (auto-height)

export function renderCalendar(events, mode, currentDate) {
  const container = document.getElementById("calendar-container");
  container.innerHTML = "";

  events = (events || []).slice().sort((a,b) => {
    const da = parseEventDate(a, "start").getTime();
    const db = parseEventDate(b, "start").getTime();
    return da - db;
  });

  if (mode === "day") renderDay(events, container, currentDate);
  else if (mode === "week") renderWeek(events, container, currentDate);
  else renderMonth(events, container, currentDate);
}

/* ---------------- HELPERS ---------------- */

function parseEventDate(ev, which = "start") {
  const obj = ev?.[which];
  if (!obj) return new Date(0);
  if (obj.date) {
    const [y, m, d] = obj.date.split("-").map(Number);
    return new Date(y, m - 1, d);
  } else if (obj.dateTime) {
    return new Date(obj.dateTime);
  } else {
    return new Date(0);
  }
}

function minutesFromMidnightLocal(d) {
  return d.getHours() * 60 + d.getMinutes();
}
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

/* ---------------- MONTH (dots / indicators) ---------------- */

function renderMonth(events, container, currentDate) {
  const grid = document.createElement("div");
  grid.className = "month-grid";

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const startIndex = (firstOfMonth.getDay() + 6) % 7; // monday-start
  const total = 42;

  // events by local date (YYYY-MM-DD)
  const eventsByDate = {};
  for (const ev of events) {
    const dt = parseEventDate(ev, "start");
    const sd = dt.getFullYear() + '-' + String(dt.getMonth()+1).padStart(2,'0') + '-' + String(dt.getDate()).padStart(2,'0');
    if (!eventsByDate[sd]) eventsByDate[sd] = [];
    eventsByDate[sd].push(ev);
  }

  const maxDots = 4;

  for (let i = 0; i < total; i++) {
    const dayOffset = i - startIndex;
    const d = new Date(year, month, 1 + dayOffset);
    const dStr = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');

    const cell = document.createElement("div");
    cell.className = "month-cell";
    if (d.getMonth() !== month) cell.classList.add("other-month");

    // Добавляем data-date для клика
    cell.dataset.date = dStr;

    const dateEl = document.createElement("div");
    dateEl.className = "cell-date";
    dateEl.textContent = d.getDate();
    cell.appendChild(dateEl);

    const evs = eventsByDate[dStr] || [];
    if (evs.length) {
      const dotsRow = document.createElement("div");
      dotsRow.className = "cell-dots";
      dotsRow.style.display = "flex";
      dotsRow.style.gap = "6px";
      dotsRow.style.alignItems = "center";
      dotsRow.style.marginTop = "auto";

      const visible = Math.min(evs.length, maxDots);
      for (let k = 0; k < visible; k++) {
        const ev = evs[k];
        const dot = document.createElement("span");
        dot.className = "month-dot";
        dot.title = buildTooltip(ev);

        // Добавляем data-атрибут для клика по событию
        dot.dataset.title = ev.summary || "";
        dot.dataset.time = ev.start?.dateTime ? parseEventDate(ev,"start").toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : "";
        dot.dataset.description = ev.description || "";

        dotsRow.appendChild(dot);
      }
      if (evs.length > maxDots) {
        const more = document.createElement("span");
        more.className = "month-more";
        more.textContent = `+${evs.length - maxDots}`;
        more.title = evs.map(x => (x.summary || "")).join("\n");
        more.style.color = "var(--muted)";
        more.style.fontSize = "12px";
        dotsRow.appendChild(more);
      }

      cell.appendChild(dotsRow);
    }

    grid.appendChild(cell);
  }

  container.appendChild(grid);
}


/* ---------------- WEEK (full visible events) ---------------- */

function renderWeek(events, container, currentDate) {
  const wrapper = document.createElement("div");
  wrapper.className = "week-table";

  const timeCol = document.createElement("div");
  timeCol.className = "time-column";

  const daysGrid = document.createElement("div");
  daysGrid.className = "week-days-grid";

  const start = new Date(currentDate);
  const shift = (start.getDay() + 6) % 7;
  start.setDate(start.getDate() - shift);

  const eventsByDate = {};
  for (const ev of events) {
    const sd = parseEventDate(ev, "start").toISOString().slice(0,10);
    if (!eventsByDate[sd]) eventsByDate[sd] = [];
    eventsByDate[sd].push(ev);
  }

  const rootStyle = getComputedStyle(document.documentElement);
  const hourHeightRaw = rootStyle.getPropertyValue('--hour-height') || '48px';
  const hourHeight = parseFloat(hourHeightRaw);

  for (let i = 0; i < 7; i++) {
    const day = new Date(start);
    day.setDate(start.getDate() + i);
    const key = day.toISOString().slice(0,10);

    const col = document.createElement("div");
    col.className = "week-col";
    col.dataset.date = key; // <- дата для клика

    const header = document.createElement("div");
    header.className = "week-col-header";
    header.textContent = day.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "short" });
    col.appendChild(header);

    const slotContainer = document.createElement("div");
    slotContainer.className = "week-slot-container";
    slotContainer.style.position = "relative";
    slotContainer.style.height = `${24 * hourHeight}px`;
    slotContainer.style.boxSizing = "border-box";

    const evs = eventsByDate[key] || [];
    for (const ev of evs) {
      const s = parseEventDate(ev, "start");
      const e = parseEventDate(ev, "end") || new Date(s.getTime() + 30*60000);
      const startMin = clamp(minutesFromMidnightLocal(s), 0, 24*60);
      const endMin = clamp(minutesFromMidnightLocal(e), 0, 24*60);
      const durationMin = Math.max(15, endMin - startMin);
      const topPx = startMin * (hourHeight / 60);
      let heightPx = durationMin * (hourHeight / 60);

      const evEl = document.createElement("div");
      evEl.className = "event";
      evEl.dataset.title = ev.summary || "Без названия";
      evEl.dataset.time = formatTimeRange(ev);
      evEl.dataset.description = ev.description || "";
      evEl.style.whiteSpace = "normal";
      evEl.style.wordBreak = "break-word";
      evEl.style.position = "absolute";
      evEl.style.left = "6px";
      evEl.style.right = "6px";
      evEl.style.top = `${topPx}px`;
      evEl.style.height = `${Math.max(heightPx, 24)}px`;
      evEl.style.boxSizing = "border-box";
      evEl.style.overflow = "visible";
      evEl.style.zIndex = 3;
      evEl.style.background = "rgba(255,255,255,0.98)";
      evEl.style.padding = "6px 8px";
      evEl.style.borderRadius = "6px";
      evEl.style.boxShadow = "0 1px 0 rgba(16,24,40,0.03)";

      evEl.innerHTML = `<div style="font-weight:600; margin-bottom:4px">${ev.summary || "Без названия"}</div>
                        <div style="font-size:12px; opacity:.85">${s.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} – ${e.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>`;

      slotContainer.appendChild(evEl);

      const contentHeight = evEl.scrollHeight;
      const desiredHeight = Math.max(heightPx, contentHeight + 4);
      evEl.style.height = `${desiredHeight}px`;
    }

    col.appendChild(slotContainer);
    daysGrid.appendChild(col);
  }

  wrapper.appendChild(timeCol);
  wrapper.appendChild(daysGrid);
  container.appendChild(wrapper);

  const firstHeader = daysGrid.querySelector('.week-col .week-col-header');
  const headerHeight = firstHeader ? firstHeader.getBoundingClientRect().height : 0;
  timeCol.style.paddingTop = `${headerHeight}px`;

  timeCol.innerHTML = "";
  for (let h = 0; h < 24; h++) {
    const t = document.createElement("div");
    t.className = "time-label";
    t.style.height = `${hourHeight}px`;
    t.textContent = `${String(h).padStart(2,'0')}:00`;
    timeCol.appendChild(t);
  }
}

/* ---------------- DAY (full visible events) ---------------- */

function renderDay(events, container, currentDate) {
  const wrap = document.createElement("div");
  wrap.className = "day-table";

  const timeCol = document.createElement("div");
  timeCol.className = "time-column";

  const eventsCol = document.createElement("div");
  eventsCol.className = "day-events-col";
  eventsCol.style.position = "relative";
  eventsCol.style.height = '';

  const rootStyle = getComputedStyle(document.documentElement);
  const hourHeightRaw = rootStyle.getPropertyValue('--hour-height') || '48px';
  const hourHeight = parseFloat(hourHeightRaw);

  for (let h = 0; h < 24; h++) {
    const t = document.createElement("div");
    t.className = "time-label";
    t.style.height = `${hourHeight}px`;
    t.textContent = `${String(h).padStart(2, '0')}:00`;
    timeCol.appendChild(t);

    const slot = document.createElement("div");
    slot.className = "day-slot";
    slot.style.height = `${hourHeight}px`;
    eventsCol.appendChild(slot);
  }
  eventsCol.style.height = `${24 * hourHeight}px`;

  for (const ev of events) {
    const s = parseEventDate(ev, "start");
    const e = parseEventDate(ev, "end") || new Date(s.getTime() + 30*60000);
    const startMin = clamp(minutesFromMidnightLocal(s), 0, 24*60);
    const endMin = clamp(minutesFromMidnightLocal(e), 0, 24*60);
    const durationMin = Math.max(15, endMin - startMin);
    const topPx = startMin * (hourHeight / 60);
    let heightPx = durationMin * (hourHeight / 60);

    const evEl = document.createElement("div");
    evEl.className = "event";
    evEl.dataset.title = ev.summary || "Без названия";
    evEl.dataset.time = formatTimeRange(ev);
    evEl.dataset.description = ev.description || "";

    evEl.style.whiteSpace = "normal";
    evEl.style.wordBreak = "break-word";
    evEl.style.position = "absolute";
    evEl.style.left = "6px";
    evEl.style.right = "6px";
    evEl.style.top = `${topPx}px`;
    evEl.style.height = `${Math.max(24, heightPx)}px`;
    evEl.style.boxSizing = "border-box";
    evEl.style.overflow = "visible";
    evEl.style.zIndex = 3;
    evEl.style.background = "rgba(255,255,255,0.98)";
    evEl.style.padding = "6px 8px";
    evEl.style.borderRadius = "6px";
    evEl.style.boxShadow = "0 1px 0 rgba(16,24,40,0.03)";

    evEl.innerHTML = `<div class="title" style="font-weight:600">${ev.summary || "Без названия"}</div>
                      <div class="time" style="font-size:12px; opacity:.85">${s.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} – ${e.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>`;

    eventsCol.appendChild(evEl);

    const contentHeight = evEl.scrollHeight;
    const desiredHeight = Math.max(heightPx, contentHeight + 4);
    evEl.style.height = `${desiredHeight}px`;
  }

  wrap.appendChild(timeCol);
  wrap.appendChild(eventsCol);
  container.appendChild(wrap);
}

/* ---------------- small helpers ---------------- */

function buildTooltip(ev) {
  const s = parseEventDate(ev, "start");
  const e = parseEventDate(ev, "end") || null;
  const time = ev.start?.dateTime ? s.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : "";
  return `${time} ${ev.summary || ""}`.trim();
}

function formatMaybeLocationOrDesc(ev) {
  if (ev.location) return ev.location;
  if (ev.description) return ev.description.split('\n')[0];
  return "";
}

function formatTimeRange(ev) {
  const s = parseEventDate(ev, "start");
  const e = parseEventDate(ev, "end") || new Date(s.getTime() + 30*60000);
  return `${s.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} – ${e.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
}
