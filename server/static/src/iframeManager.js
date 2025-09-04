export async function renderCalendar(containerEl, { calendarId, mode, date }) {
  containerEl.innerHTML = '<div class="loader">Загрузка календаря…</div>';

  try {
    const res = await fetch(`http://localhost:8000/api/calendar?cid=${calendarId}&tz=${timezone}`);
    if (!res.ok) throw new Error('Ошибка сервера');
    const data = await res.json();

    if (data.error) throw new Error(data.error);

    // Рендерим список событий в том же блоке
    if (data.events && data.events.length) {
      const html = data.events.map(ev => {
        const start = new Date(ev.start.dateTime || ev.start.date);
        const end = new Date(ev.end?.dateTime || ev.end?.date || start);

        return `
          <div class="event">
            <div class="event-time">
              ${start.toLocaleDateString('ru-RU', { day:'2-digit', month:'2-digit' })}
              ${start.toLocaleTimeString('ru-RU', { hour:'2-digit', minute:'2-digit' })}
              –
              ${end.toLocaleTimeString('ru-RU', { hour:'2-digit', minute:'2-digit' })}
            </div>
            <div class="event-title">
              ${ev.summary || '(без названия)'}
            </div>
          </div>
        `;
      }).join('');

      containerEl.innerHTML = `<div class="events-list">${html}</div>`;
    } else {
      containerEl.innerHTML = '<div>Событий нет</div>';
    }
  } catch(e) {
    containerEl.innerHTML = `<div>Ошибка: ${e.message}</div>`;
  }
}
