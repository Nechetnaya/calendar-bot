from datetime import datetime

import openai
import os
import json
import logging
import pytz


logger = logging.getLogger(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


async def parse_user_message(text: str, user_timezone: str) -> dict:
    """
    Отправляет текст пользователя LLM и получает JSON с intent и сущностями.
    """
    # Получаем текущее время в таймзоне пользователя
    now = datetime.now(pytz.timezone(user_timezone))
    now_iso = now.isoformat()

    prompt = f"""
    Ты — парсер сообщений календаря. Верни JSON с intent и сущностями.

    Текст пользователя: "{text}"
    Таймзона: {user_timezone}
    Сейчас: {now_iso}

    Формат JSON:
    {{
        "intent": "create_event | query_schedule | find_free_time | track_delivery",
        "title": "только текст события без даты",
        "start": "ISO8601 дата и время начала,
        "end": "ISO8601 дата и время конца",
        "time_min": "ISO8601 начало периода для query_schedule и find_free_time, если указано",
        "time_max": "ISO8601 конец периода для query_schedule и find_free_time, если указано",
        "location": null,
        "description": null
    }}
    
    Правила парсинга даты и времени:
    - Всегда используй {now_iso} как "сейчас" (например для расчёта "сегодня/завтра/пятницу/через n часов").
    - Всегда возвращай временные поля в ISO8601 (YYYY-MM-DDTHH:MM:SS±HH:MM) с учётом таймзоны пользователя.
    - Если пользователь написал дату или время в тексте — помещай их в "start" и "end" (таймзона пользователя).
    - Если есть время, но нет даты → используй дату сегодня (в таймзоне пользователя).
    - Если есть дата, но нет времени → используем 09:00 как start и 10:00 как end (таймзона пользователя).
    - Дата окончания - start + продолжительность 
    - Если время окончания не указано для create_event → добавляй 1 час к start.
    - Если время **не указано** для query_schedule и find_free_time — используй начало и конец дня (00:00 – 23:59) в таймзоне пользователя.
    - Если дата относительная ("завтра", "в пятницу")  — преобразуй её в точную будущую дату с учётом таймзоны.
    - Если дата < {now_iso}, добавляй + к дате + 1 год
    - Распознавай форматы времени: "9:00", "9", "9 00", "9.00", "9 часов", "9 утра", "3 дня", "7 вечера".
    - Если нет даты и времени → оставь start и end (или time_min/time_max) равными null.
    - Если не удалось определить title — верни title = null.
    - Старайся извлечь location, если пользователь указал адрес/место/метро/улицу.
    
    Правила для формирования json:
    - убирай из title дату и время 
    - дополнительную информацию относи в description
    - Всегда возвращай поле "intent".
    - Для intent == "create_event":
      - Если title == null → верни JSON с title=null (и другими полями, если распознаны).
      - Если start == null и end == null → верни JSON с start=null и end=null.
    - Для intent in ("query_schedule","find_free_time"):
      - Если time_min == null и time_max == null → верни JSON с time_min=null и time_max=null.
    - Не добавляй ничего кроме указанных полей. Возвращай **только** валидный JSON.
    """

    logger.info("Отправляю в LLM")

    response = openai.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}],
        # temperature=0
    )

    text_response = response.choices[0].message.content.strip()
    logger.info(f"Ответ LLM: {text_response}")

    try:
        result = json.loads(text_response)
    except json.JSONDecodeError:
        logger.error("LLM вернула невалидный JSON")
        result = {"intent": "unknown", "raw": text_response}

    return result
