// src/utils.js
export function getQueryParams() {
  const q = new URLSearchParams(location.search);
  return {
    cid: q.get('cid') || null,     // calendar id
    tz: q.get('tz') || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    view: q.get('view') || 'month'
  };
}

export function formatPeriodLabel(mode, date) {
  // date is JS Date
  if (!date) date = new Date();
  const opts = { month: 'long', year: 'numeric' };
  if (mode === 'month') {
    return date.toLocaleDateString('ru-RU', opts);
  } else if (mode === 'week') {
    // compute week start/end (Mon-Sun)
    const start = new Date(date);
    const day = start.getDay();
    const diff = (day === 0 ? -6 : 1) - day; // set Monday as first day
    start.setDate(start.getDate() + diff);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    const s = start.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' });
    const e = end.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' });
    return `${s} — ${e}`;
  } else {
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
  }
}

export function dateToYMD(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth()+1).padStart(2,'0');
  const d = String(date.getDate()).padStart(2,'0');
  return `${y}${m}${d}`;
}
