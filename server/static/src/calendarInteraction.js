// src/calendarInteraction.js
// Отвечает за клики: день -> dispatch 'open-day', событие -> показывает модалку

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("calendar-container");

  // Создаём простую модалку (одна на весь документ)
  const modal = document.createElement("div");
  modal.id = "event-modal";
  Object.assign(modal.style, {
    position: "fixed", inset: "0", display: "none",
    justifyContent: "center", alignItems: "center",
    background: "rgba(0,0,0,0.35)", zIndex: 9999
  });

  const card = document.createElement("div");
  Object.assign(card.style, {
    background: "white", padding: "18px", borderRadius: "10px",
    maxWidth: "480px", width: "92%", boxSizing: "border-box",
    boxShadow: "0 8px 30px rgba(16,24,40,0.12)", position: "relative"
  });

  const closeBtn = document.createElement("button");
  closeBtn.textContent = "Закрыть";
  Object.assign(closeBtn.style, {
    position: "absolute", top: "10px", right: "10px",
    border: "none", background: "rgba(0,0,0,0.04)", padding: "6px 8px",
    borderRadius: "6px", cursor: "pointer"
  });
  closeBtn.addEventListener("click", () => { modal.style.display = "none"; });

  const body = document.createElement("div");
  body.id = "event-modal-body";

  card.appendChild(closeBtn);
  card.appendChild(body);
  modal.appendChild(card);
  document.body.appendChild(modal);

  function openModal(data) {
    body.innerHTML = `
      <h3 style="margin:0 0 8px">${escapeHtml(data.title || "Событие")}</h3>
      ${data.time ? `<div style="color:var(--muted); margin-bottom:8px">${escapeHtml(data.time)}</div>` : ""}
      ${data.location ? `<div style="font-size:13px; margin-bottom:8px">${escapeHtml(data.location)}</div>` : ""}
      ${data.description ? `<div style="font-size:13px; color: #222">${escapeHtml(data.description)}</div>` : ""}
    `;
    modal.style.display = "flex";
  }

  // утилита для безопасности текста
  function escapeHtml(s){ return String(s||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;"); }

  // Клики внутри контейнера календаря
  container.addEventListener("click", (e) => {
    const evEl = e.target.closest(".event");
    if (evEl) {
      // кликнули на событие — откроем модалку с данными из data-атрибутов
      const data = {
        title: evEl.dataset.title || evEl.textContent.trim(),
        time: evEl.dataset.time || "",
        description: evEl.datasetDescription || evEl.dataset.description || "",
        location: evEl.dataset.location || ""
      };
      openModal(data);
      return;
    }

    // кликнули на ячейку месяца или колонку недели — откроем day view
    const dayCell = e.target.closest(".month-cell, .week-col");
    if (dayCell) {
      const date = dayCell.dataset?.date;
      if (date) {
        // посылаем событие для main.js
        const ev = new CustomEvent("open-day", { detail: { date } });
        document.dispatchEvent(ev);
      }
    }
  });

  // закрыть модалку при клике вне карточки
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.style.display = "none";
  });
});
