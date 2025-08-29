import re
from collections import namedtuple

ParsedTime = namedtuple("ParsedTime", ["hour", "minute", "fragment"])

def parse_time_from_text(text: str) -> ParsedTime | None:
    """
    Ищет время в тексте и возвращает (hour, minute, фрагмент для удаления)
    Поддерживается:
      - 8
      - 8:00
      - 8.00
      - 8 00
      - в 8 утра / вечера
      - 20 часов
    """
    patterns = [
        r'\b(\d{1,2})[:.\s](\d{2})\b',  # 17:30, 17.30, 17 30
        r'\b(\d{1,2})\b',  # просто 17
        r'\b(\d{1,2})\s*(час|часа|часов|минут|минуты)?\b',  # 17 часов, 10 минут
        r'\b(час|полчаса)\b'  # час, полчаса
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
            # учитываем утро/вечер
            meridian_match = re.search(r'утра|вечера', text.lower())
            if meridian_match and 'вечера' in meridian_match.group(0).lower() and hour < 12:
                hour += 12
            return ParsedTime(hour=hour, minute=minute, fragment=match.group(0))
    return None
