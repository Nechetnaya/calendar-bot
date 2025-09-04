import { renderCalendar } from "./calendarView.js";
import "./calendarInteraction.js";


const urlParams = new URLSearchParams(window.location.search);
const calendarId = urlParams.get("cid") || "primary";
const timezone = urlParams.get("tz") || Intl.DateTimeFormat().resolvedOptions().timeZone;

let mode = "month";
let currentDate = new Date();
let events = [];

const loaderEl = document.getElementById("loader");
const calendarContainer = document.getElementById("calendar-container");

// Функция рендеринга + обновление периода
function render() {
  renderCalendar(events, mode, currentDate);
  updateCurrentPeriod();
}

// Загрузка событий с API
async function loadEvents() {
  loaderEl.style.display = "block";
  try {
    // для month — отправляем диапазон видимой сетки (6 недель)
    let query = `cid=${encodeURIComponent(calendarId)}&tz=${encodeURIComponent(timezone)}&mode=${mode}`;
    if (mode === "month") {
      // вычисляем старт первой видимой клетки (понедельник первой недели отображения)
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
      const firstOfMonth = new Date(year, month, 1);
      const startOffset = (firstOfMonth.getDay() + 6) % 7; // 0..6, 0=Mon
      const firstVisible = new Date(year, month, 1 - startOffset);
      const lastVisible = new Date(firstVisible);
      lastVisible.setDate(firstVisible.getDate() + 41); // 6*7 -1
      query += `&start=${firstVisible.toISOString().slice(0,10)}&end=${new Date(lastVisible.getFullYear(), lastVisible.getMonth(), lastVisible.getDate()+1).toISOString().slice(0,10)}`; // end exclusive
    } else {
      // для week/day — отправляем date (бэку по-прежнему удобней)
      const dateStr = currentDate.toISOString().slice(0, 10);
      query += `&date=${dateStr}`;
    }

    const res = await fetch(`/api/calendar?${query}`);
    if (!res.ok) throw new Error("Ошибка сервера");
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    events = data.events || [];
    render(); // render() вызывает renderCalendar + updateCurrentPeriod
  } catch (err) {
    console.error("Ошибка загрузки:", err);
    calendarContainer.innerHTML = `<div class="error">Ошибка: ${err.message}</div>`;
  } finally {
    loaderEl.style.display = "none";
  }
}


// Обновление текущего периода (между стрелками)
function updateCurrentPeriod() {
  const el = document.getElementById("current-period");

  if (mode === "day") {
    el.textContent = currentDate.toLocaleDateString("ru-RU", { day:"2-digit", month:"short", year:"numeric" });
  } else if (mode === "week") {
    const start = new Date(currentDate);
    start.setDate(currentDate.getDate() - currentDate.getDay()); // начало недели (воскресенье)
    const end = new Date(start);
    end.setDate(start.getDate() + 6); // конец недели (суббота)
    el.textContent = `${start.toLocaleDateString("ru-RU", { day:"2-digit", month:"short" })} – ${end.toLocaleDateString("ru-RU", { day:"2-digit", month:"short" })}`;
  } else if (mode === "month") {
    el.textContent = currentDate.toLocaleDateString("ru-RU", { month:"long", year:"numeric" });
  }
}

// Навигация стрелками
document.getElementById("prev").addEventListener("click", () => {
  if (mode === "month") currentDate.setMonth(currentDate.getMonth() - 1);
  else if (mode === "week") currentDate.setDate(currentDate.getDate() - 7);
  else currentDate.setDate(currentDate.getDate() - 1);
  loadEvents();
});

document.getElementById("next").addEventListener("click", () => {
  if (mode === "month") currentDate.setMonth(currentDate.getMonth() + 1);
  else if (mode === "week") currentDate.setDate(currentDate.getDate() + 7);
  else currentDate.setDate(currentDate.getDate() + 1);
  loadEvents();
});

// Переключение режимов
document.getElementById("btn-month").addEventListener("click", () => {
  mode = "month";
  setActive("btn-month");
  loadEvents();
});

document.getElementById("btn-week").addEventListener("click", () => {
  mode = "week";
  setActive("btn-week");
  loadEvents();
});

document.getElementById("btn-day").addEventListener("click", () => {
  mode = "day";
  setActive("btn-day");
  loadEvents();
});

// Выбор даты через календарь
document.getElementById("date-picker").addEventListener("change", (e) => {
  currentDate = new Date(e.target.value);
  mode = "day";
  setActive("btn-day");
  loadEvents();
});

// Подсветка активного режима
function setActive(id) {
  document.querySelectorAll(".mode-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}
// -----------------------------
// Слушаем событие open-day от calendarInteraction.js
document.addEventListener("open-day", (e) => {
  const dateStr = e.detail?.date;
  if (!dateStr) return;
  currentDate = new Date(dateStr);
  mode = "day";
  setActive("btn-day");
  // синхронизируем date-picker если есть
  const dp = document.getElementById("date-picker");
  if (dp) dp.value = dateStr;
  loadEvents();
});


// Старт
loadEvents();
