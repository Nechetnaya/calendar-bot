// src/ui.js
import { renderCalendar } from './iframeManager.js';
import { formatPeriodLabel } from './utils.js';

export function initUI({calendarId, container}) {
  const btnMonth = document.getElementById('btn-month');
  const btnWeek = document.getElementById('btn-week');
  const btnDay = document.getElementById('btn-day');
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');
  const datePicker = document.getElementById('date-picker');
  const currentPeriod = document.getElementById('current-period');

  let mode = 'month';
  let anchorDate = new Date();

  async function refresh() {
    currentPeriod.textContent = formatPeriodLabel(mode, anchorDate);
    await renderCalendar(container, { calendarId, mode, date: anchorDate });
  }

  function setMode(m) {
    mode = m;
    [btnMonth, btnWeek, btnDay].forEach(b => b.classList.remove('active'));
    if (m === 'month') btnMonth.classList.add('active');
    if (m === 'week') btnWeek.classList.add('active');
    if (m === 'day') btnDay.classList.add('active');
    refresh();
  }

  btnMonth.addEventListener('click', ()=> setMode('month'));
  btnWeek.addEventListener('click', ()=> setMode('week'));
  btnDay.addEventListener('click', ()=> setMode('day'));

  prev.addEventListener('click', ()=>{
    if (mode === 'month') anchorDate.setMonth(anchorDate.getMonth()-1);
    else anchorDate.setDate(anchorDate.getDate() - (mode==='week'?7:1));
    refresh();
  });
  next.addEventListener('click', ()=>{
    if (mode === 'month') anchorDate.setMonth(anchorDate.getMonth()+1);
    else anchorDate.setDate(anchorDate.getDate() + (mode==='week'?7:1));
    refresh();
  });

  datePicker.valueAsDate = anchorDate;
  datePicker.addEventListener('change', ()=> {
    const d = datePicker.valueAsDate;
    if (d) anchorDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    refresh();
  });

  refresh();
}
