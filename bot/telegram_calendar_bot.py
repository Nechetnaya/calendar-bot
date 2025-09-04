import os
import logging
import asyncio
import pytz
import re
import json
from datetime import datetime, timedelta
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from dateparser.search import search_dates
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler
from urllib.parse import quote_plus

from bot.user_manager import UserManager
from bot.time_parser import parse_time_from_text
from bot.llm_parser import parse_user_message
from bot.google_calendar_manager import GoogleCalendarManager


# ---------------- ЛОГИ ----------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- ФУНКЦИИ ----------------
def parse_timezone(input_str: str):
    input_str = input_str.strip()
    # UTC смещение
    match = re.match(r'([+-]?\d{1,2})$', input_str)
    if match:
        offset_hours = int(match.group(1))
        return f"Etc/GMT{-offset_hours:+d}"
    # По названию города
    try:
        geolocator = Nominatim(user_agent="timezone_bot", timeout=10)
        location = geolocator.geocode(input_str)
        if location:
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            if tz_name:
                return tz_name
    except Exception:
        pass
    # Поиск по частичному совпадению
    for tz in pytz.all_timezones:
        if input_str.lower() in tz.lower():
            return tz
    return None


def parse_date_range(text_lower, now, user_tz):
    months = {
        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5,
        'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10,
        'ноября': 11, 'декабря': 12
    }
    weekdays = {
        'понедельника': 0, 'вторника': 1, 'среды': 2, 'четверга': 3,
        'пятницы': 4, 'субботы': 5, 'воскресенья': 6
    }

    start_datetime = None
    end_datetime = None

    # --- диапазон дат: числа/текст/год ---
    date_range_match = re.search(
        r'с\s+(\d{1,2})(?:[.](\d{1,2}))?\s*(\w+)?(?:\s*(\d{4}))?\s*(?:по|-)\s+(\d{1,2})(?:[.](\d{1,2}))?\s*(\w+)?(?:\s*(\d{4}))?',
        text_lower
    )

    if date_range_match:
        start_day = int(date_range_match.group(1))
        start_month_num = date_range_match.group(2)
        start_month_text = date_range_match.group(3)
        start_year_num = date_range_match.group(4)
        end_day = int(date_range_match.group(5))
        end_month_num = date_range_match.group(6)
        end_month_text = date_range_match.group(7)
        end_year_num = date_range_match.group(8)

        start_month = int(start_month_num) if start_month_num else months.get(start_month_text, now.month)
        end_month = int(end_month_num) if end_month_num else months.get(end_month_text, start_month)

        start_year = int(start_year_num) if start_year_num else now.year
        end_year = int(end_year_num) if end_year_num else start_year

        start_datetime = user_tz.localize(datetime(start_year, start_month, start_day, 9, 0))
        end_datetime = user_tz.localize(datetime(end_year, end_month, end_day, 18, 0))
        text_lower = text_lower.replace(date_range_match.group(0), '')

    # --- дни недели ---
    if not start_datetime:
        m = re.search(r'с\s+(\w+)\s*(?:до|по)\s*(\w+)', text_lower)
        if m and m.group(1) in weekdays and m.group(2) in weekdays:
            start_weekday = weekdays[m.group(1)]
            end_weekday = weekdays[m.group(2)]
            days_ahead = (start_weekday - now.weekday() + 7) % 7
            start_datetime = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
            days_diff = (end_weekday - start_weekday + 7) % 7
            end_datetime = (start_datetime + timedelta(days=days_diff)).replace(hour=18, minute=0)
            text_lower = text_lower.replace(m.group(0), '')

    return text_lower, start_datetime, end_datetime


def parse_event_datetime(text: str, user_timezone: str):
    user_tz = pytz.timezone(user_timezone)
    text_lower = text.lower()
    now = datetime.now(pytz.utc).astimezone(user_tz)

    start_time_range = None
    end_time_range = None

    text_lower, start_datetime, end_datetime = parse_date_range(text_lower, now, user_tz)
    # --- если диапазон дат не найден, ищем одиночную дату ---
    if not start_datetime:
        # старая логика с today/tomorrow/послезавтра, DD.MM, search_dates

        # --- поиск диапазона времени "с 10 до 15" ---
        time_range = re.search(
            r'(?:с|от)\s*(\d{1,2}(?:[:.\s]\d{2})?)\s*(?:до|-)\s*(\d{1,2}(?:[:.\s]\d{2})?)',
            text_lower
        )
        if time_range:
            start_time_range = time_range.group(1)
            end_time_range = time_range.group(2)
            text_lower = text_lower.replace(time_range.group(0), '')

        # --- ключевые слова "сегодня", "завтра", "послезавтра" ---
        # "через N час/минут"
        match = re.search(r'через\s+((\d+)\s*(часa|часов|час|минуты|минут)|полчаса)', text_lower)
        if match:
            fragment = match.group(0)
            if 'полчаса' in fragment:
                delta = timedelta(minutes=30)
            elif 'час' in fragment and not re.search(r'\d+', fragment):
                delta = timedelta(hours=1)
            else:
                amount = int(match.group(2))
                unit = match.group(3)
                if unit and 'мин' in unit:
                    delta = timedelta(minutes=amount)
                else:
                    delta = timedelta(hours=amount)

            start_datetime = now + delta
            end_datetime = start_datetime + timedelta(hours=1)

            # Убираем весь фрагмент, включая пробелы вокруг
            event_title = re.sub(r'\s*' + re.escape(fragment) + r'\s*', ' ', text_lower, flags=re.IGNORECASE).strip()
            if not event_title:
                event_title = "Напоминание"

            return event_title, start_datetime, end_datetime

        elif "сегодня" in text_lower:
            start_datetime = now.replace(second=0, microsecond=0)
        elif "завтра" in text_lower:
            start_datetime = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            text_lower = text_lower.replace("завтра", "")
        elif "послезавтра" in text_lower:
            start_datetime = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
            text_lower = text_lower.replace("послезавтра", "")
        else:
            # --- сначала пробуем регулярку DD.MM ---
            date_match = re.search(r'\b(\d{1,2})[.](\d{1,2})\b', text_lower)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = now.year
                start_datetime = user_tz.localize(datetime(year, month, day))
                text_lower = text_lower.replace(date_match.group(0), '')
            else:
                # --- обычный парсинг через search_dates ---
                dates = search_dates(
                    text_lower,
                    languages=['ru'],
                    settings={'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'}
                )
                if dates:
                    start_datetime = dates[0][1]
                    # если год не указан, берем текущий
                    if start_datetime.year == 1900:
                        start_datetime = start_datetime.replace(year=now.year)
                    text_lower = text_lower.replace(dates[0][0], '')
                else:
                    start_datetime = None


    parsed_time = parse_time_from_text(text_lower)
    if parsed_time:
        hour = parsed_time.hour
        minute = parsed_time.minute
        fragment = parsed_time.fragment

        if start_datetime is None:
            start_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            start_datetime = start_datetime.replace(hour=hour, minute=minute)

        # удаляем время из текста для заголовка
        text_lower = text_lower.replace(fragment, '').strip()

        # удаляем распознанное время из текста
        # ищем все варианты: "в 7 вечера", "7 вечера", "7:00", "7.00", "7 00", "7 часов"
        time_patterns = [
            r'\bв\s*\d{1,2}\s*(?:утра|вечера)?\b',
            r'\b\d{1,2}\s*(?:утра|вечера)\b',
            r'\b\d{1,2}[:.]\d{2}\b',
            r'\b\d{1,2}\s\d{2}\b',
            r'\b\d{1,2}\s*час(?:ов|а)?\b'
        ]

        for p in time_patterns:
            text_lower = re.sub(p, '', text_lower, flags=re.IGNORECASE)

        # убираем лишние пробелы
        text_lower = re.sub(r'\s+', ' ', text_lower).strip()

    # --- если дата указана, но без времени ---
    if start_datetime and start_datetime.hour == 0 and start_datetime.minute == 0 and not start_time_range:
        start_datetime = start_datetime.replace(hour=9, minute=0)

    # --- проверка, удалось ли распознать дату ---
    if start_datetime is None:
        raise ValueError("Дата и время не распознаны, уточните, пожалуйста")

    # --- применяем таймзону ---
    if start_datetime.tzinfo is None:
        start_datetime = user_tz.localize(start_datetime)
    else:
        start_datetime = start_datetime.astimezone(user_tz)

    # --- диапазон времени ---
    if start_time_range and end_time_range:
        def fmt(s):
            parts = [int(x) for x in re.split(r'[:.\s]', s) if x.strip()]
            return parts[0], parts[1] if len(parts) > 1 else 0

        h1, m1 = fmt(start_time_range)
        h2, m2 = fmt(end_time_range)
        start_datetime = start_datetime.replace(hour=h1, minute=m1)
        end_datetime = start_datetime.replace(hour=h2, minute=m2)

        if start_datetime.tzinfo is None:
            start_datetime = user_tz.localize(start_datetime)
        if end_datetime.tzinfo is None:
            end_datetime = user_tz.localize(end_datetime)
    else:
        # добавляем +1 час только если end_datetime ещё не задан
        if not end_datetime:
            end_datetime = start_datetime + timedelta(hours=1)
            if end_datetime.tzinfo is None:
                end_datetime = user_tz.localize(end_datetime)

    # --- заголовок события: остаток текста ---
    event_title = text_lower.strip() or "Напоминание"

    return event_title, start_datetime, end_datetime


def _iso_to_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


# ---------------- КЛАСС БОТА ----------------
class TelegramCalendarBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден")

        self.calendar_manager = GoogleCalendarManager()
        self.user_manager = UserManager()

    @staticmethod
    async def handle_email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['waiting_for'] = 'email'
        await update.message.reply_text("Введите ваш email:")

    @staticmethod
    async def handle_timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['waiting_for'] = 'timezone'
        await update.message.reply_text("Введите ваш часовой пояс (например Moscow или +3):")

    @staticmethod
    async def handle_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['waiting_for'] = 'reminder'
        await update.message.reply_text("За сколько минут до события присылать напоминание?")

    @staticmethod
    async def handle_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /schedule - запрос даты для просмотра мероприятий"""
        context.user_data['waiting_for'] = 'schedule_date'
        await update.message.reply_text(
            "Введите дату для просмотра мероприятий (например, сегодня, завтра или 30.08.2025):")

    async def handle_calendar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user_data = self.user_manager.get_user(user_id) or {}

        calendar_id = user_data.get('calendar_id')
        timezone = user_data.get('timezone', 'UTC')

        if not calendar_id:
            await update.message.reply_text(
                "У вас ещё нет связанного календаря. Сначала настройте /start или укажите email/timezone.")
            return

        # URL приложения (где развёрнуто ваше мини-приложение)
        base_url = os.getenv('WEBAPP_URL')
        # безопасно кодируем calendar_id и timezone
        webapp_url = f"{base_url}?cid={quote_plus(calendar_id)}&tz={quote_plus(timezone)}"

        keyboard = [[InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=webapp_url))]]
        await update.message.reply_text("Открыть ваш Google Calendar:", reply_markup=InlineKeyboardMarkup(keyboard))


    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = str(update.effective_user.id)
        user_data = self.user_manager.get_user(user_id)

        if not user_data:
            await update.message.reply_text(
                "Добро пожаловать! 🤖\n\n"
                "Я помогу вам создавать события в календаре.\n"
                "Для начала работы укажите ваш email:"
            )
            context.user_data['waiting_for'] = 'email'
        else:
            await update.message.reply_text(
                f"С возвращением! ✨\n\n"
                f"📧 Email: {user_data['email']}\n"
                f"🌍 Часовой пояс: {user_data['timezone']}\n"
                f"⏰ Напоминания: за {user_data['reminder_minutes']} мин\n\n"
                "Отправьте сообщение с датой и описанием события!"
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = str(query.from_user.id)

        if query.data == 'change_email':
            await query.edit_message_text("Введите новый email:")
            context.user_data['waiting_for'] = 'email'

        elif query.data == 'change_timezone':
            await query.edit_message_text("Введите ваш часовой пояс (например Moscow или +3):")
            context.user_data['waiting_for'] = 'timezone'

        elif query.data == 'change_reminder':
            await query.edit_message_text("За сколько минут до события присылать напоминание?")
            context.user_data['waiting_for'] = 'reminder'

        elif query.data == 'confirm_event':
            pending = context.user_data.get('pending_event')
            if not pending:
                await query.edit_message_text("❌ Нет события для подтверждения")
                return
            user_data = self.user_manager.get_user(user_id)

            if not user_data.get('calendar_id'):
                calendar_id = self.calendar_manager.create_user_calendar(user_data['email'],user_data['timezone'])
                self.user_manager.ensure_calendar_id(user_id, calendar_id)
                user_data['calendar_id'] = calendar_id

            if pending['end'] is None:
                pending['end'] = pending['start'] + timedelta(hours=1)

            print(f"Пользователь {user_id} создал событие: {pending}")

            event_link = self.calendar_manager.create_event(
                title=pending['title'],
                start=pending['start'],
                end=pending['end'],
                timezone=user_data['timezone'],
                user_calendar_id=user_data['calendar_id'],
                location=pending.get('location'),
                description=pending.get('description')
            )

            if event_link:
                reminder_datetime = pending['start'] - timedelta(minutes=user_data['reminder_minutes'])
                await self.schedule_reminder(
                    chat_id=query.message.chat.id,
                    event_title=pending['title'],
                    event_datetime=pending['start'],
                    reminder_datetime=reminder_datetime,
                    context=context,
                    location=pending.get('location'),
                    description=pending.get('description')
                )
                await query.edit_message_text(
                    f"✅ Событие создано!\n"
                    f"📅 {pending['title']}\n"
                    f"🕐 {pending['start'].strftime('%d.%m.%Y %H:%M')}"
                    + (f"\n📍 {pending['location']}" if pending.get('location') else "")
                    + (f"\n📝 {pending['description']}" if pending.get('description') else "")
                )
            else:
                await query.edit_message_text("❌ Ошибка при создании события")

            context.user_data.pop('pending_event', None)

        elif query.data == 'cancel_event':
            await query.edit_message_text("❌ Создание события отменено")
            context.user_data.pop('pending_event', None)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Получено сообщение от {update.effective_user.id}: {update.message.text}")
        user_id = str(update.effective_user.id)
        text = update.message.text

        user_data = self.user_manager.get_user(user_id)

        # Проверяем, ожидаем ли мы какую-то информацию от пользователя
        if 'waiting_for' in context.user_data:
            await self.handle_user_input(update, context, text)
            return

        # Проверяем, настроен ли пользователь
        #user_data = self.user_manager.get_user(user_id)
        if not user_data:
            await update.message.reply_text(
                "Сначала нужно настроить бота. Используйте команду /start"
            )
            return

        # Обработка команд
        if text.startswith('/email'):
            context.user_data['waiting_for'] = 'email'
            await update.message.reply_text("Введите ваш email:")
            return
        elif text.startswith('/timezone'):
            context.user_data['waiting_for'] = 'timezone'
            await update.message.reply_text("Введите ваш часовой пояс (например Moscow или +3):")
            return
        elif text.startswith('/alert'):
            context.user_data['waiting_for'] = 'reminder'
            await update.message.reply_text("За сколько минут до события присылать напоминание?")
            return

        # === НОВОЕ: сначала пробуем rule-based парсер ===
        # try:
        #     title, start_dt, end_dt = parse_event_datetime(text, user_data['timezone'])
        #     # parser_success = True
        #     parser_success = False
        # except ValueError:
        #     parser_success = False
        #
        #     # === Если парсер не справился, вызываем LLM ===
        # if not parser_success:

        # Если ждём уточняющий ответ от пользователя (awaiting_clarify) — обработать его первым
        if context.user_data.get('awaiting_clarify'):
            clarify = context.user_data.pop('awaiting_clarify')
            combined_text = (
                f"{clarify.get('orig_text', '')}\n\n"
                f"Предыдущее частичное распознавание: {json.dumps(clarify.get('llm_json', {}), ensure_ascii=False)}\n\n"
                f"Уточнение ({clarify.get('field')}): {text}"
            )
            input_text_for_llm = combined_text
        else:
            input_text_for_llm = text

        try:
            llm_result = await parse_user_message(input_text_for_llm, user_data['timezone'])
        except Exception as e:
            logger.exception("Ошибка при вызове LLM")
            await update.message.reply_text("Ошибка при распознавании запроса (LLM).")
            return

        logger.info("LLM intent=%s", llm_result.get('intent'))

        intent = llm_result.get("intent")

        if intent == "query_schedule":
            # получение расписания
            time_min = _iso_to_dt(llm_result['time_min'])
            time_max = _iso_to_dt(llm_result['time_max'])

            if not time_min or not time_max:
                await update.message.reply_text("Пожалуйста, уточните дату для просмотра расписания:")
                context.user_data['awaiting_clarify'] = {
                    "field": "date",
                    "llm_json": llm_result,
                    "orig_text": text
                }
                return

            events = self.calendar_manager.get_events(
                user_calendar_id=user_data.get('calendar_id'),
                time_min=time_min,
                time_max=time_max
            )
            # Можно отдать юзеру красивый текстовый список
            schedule_text = "\n".join([
                f"📌 {e['title']} — {e['start'].strftime('%d.%m %H:%M')} - {e['end'].strftime('%H:%M')}"
                for e in events
            ]) or "Нет событий в выбранный период"
            await update.message.reply_text(schedule_text)

        elif intent == "find_free_time":
            time_min = _iso_to_dt(llm_result['time_min'])
            time_max = _iso_to_dt(llm_result['time_max'])

            if not time_min or not time_max:
                await update.message.reply_text("Пожалуйста, уточните дату для просмотра расписания:")
                context.user_data['awaiting_clarify'] = {
                    "field": "date",
                    "llm_json": llm_result,
                    "orig_text": text
                }
                return

            # Получаем слоты по 1 часу с пометкой free
            slots = self.calendar_manager.get_free_slots(
                user_calendar_id=user_data.get('calendar_id'),
                time_min=time_min,
                time_max=time_max
            )
            # Формируем текст с отметкой свободен/занят
            if slots:
                slots_text = "\n".join([
                    f"🕒 {s['start'].strftime('%d.%m %H:%M')} - {s['end'].strftime('%H:%M')} — {'Свободно' if s['free'] else 'Занято'}"
                    for s in slots
                ])
            else:
                slots_text = "Нет слотов в указанном периоде"
            await update.message.reply_text(slots_text)

        elif intent == "create_event":
            start_dt = _iso_to_dt(llm_result.get('start'))
            end_dt = _iso_to_dt(llm_result.get('end'))
            title = llm_result['title']
            location = llm_result.get('location')
            description = llm_result.get('description')

            if title is None:
                # спросить название
                await update.message.reply_text("Пожалуйста, уточните название события:")
                context.user_data['awaiting_clarify'] = {
                    "field": "title",
                    "llm_json": llm_result,
                    "orig_text": text
                }
                return

            if (start_dt is None and end_dt is None):
                await update.message.reply_text("Пожалуйста, уточните дату и/или время события:")
                context.user_data['awaiting_clarify'] = {
                    "field": "datetime",
                    "llm_json": llm_result,
                    "orig_text": text
                }
                return

            context.user_data['pending_event'] = {
                'title': title,
                'start': start_dt,
                'end': end_dt,
                'location': location,
                'description': description,
            }
            pending = context.user_data['pending_event']

            if pending['end'].date() != pending['start'].date():
                date_str = f"{pending['start'].strftime('%d.%m.%Y')} — {pending['end'].strftime('%d.%m.%Y')}"
                time_str = "Весь день"
            else:
                date_str = pending['start'].strftime('%d.%m.%Y')
                time_str = f"{pending['start'].strftime('%H:%M')} — {pending['end'].strftime('%H:%M')}"

            location_str = pending.get('location') or "Не указано"
            description_str = pending.get('description') or ""

            confirm_text = (
                f"Вы хотите создать событие?\n\n"
                f"📅 {title}\n"
                f"🗓 {date_str}\n"
                f"⏰ {time_str}\n"
                f"📍 {location_str}\n"
                f"   {description_str}"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Да", callback_data='confirm_event')],
                [InlineKeyboardButton("❌ Нет", callback_data='cancel_event')]
            ]
            await update.message.reply_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_user_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        user_id = str(update.effective_user.id)
        waiting_for = context.user_data.get('waiting_for')
        user_data = self.user_manager.get_user(user_id) or {}

        # --- обработка ввода даты для /schedule ---
        if waiting_for == 'schedule_date':
            try:
                # используем ту же функцию parse_event_datetime, чтобы распознать дату
                _, start_dt, _ = parse_event_datetime(text, user_data.get('timezone', 'Europe/Moscow'))
                # приводим к формату даты без времени
                day_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                # получаем события из календаря
                events = self.calendar_manager.get_events(
                    user_calendar_id=user_data.get('calendar_id'),
                    time_min=day_start,
                    time_max=day_end
                )

                if events:
                    msg = "📅 События на этот день:\n"
                    for e in events:
                        start_time = e['start'].strftime("%H:%M")
                        end_time = e['end'].strftime("%H:%M") if e.get('end') else ""
                        msg += f"- {e['title']} ⏰ {start_time}"
                        if end_time:
                            msg += f" — {end_time}"
                        msg += "\n"
                else:
                    msg = "На этот день событий нет."

                await update.message.reply_text(msg)
                context.user_data.pop('waiting_for')

            except ValueError:
                await update.message.reply_text(
                    "❌ Некорректная дата, попробуйте снова (например: сегодня, завтра или 30.08.2025)")

            return

        if waiting_for == 'email':
            if '@' in text and '.' in text:
                user_data = self.user_manager.get_user(user_id) or {
                    'timezone': 'Europe/Moscow',
                    'reminder_minutes': 10
                }
                user_data['email'] = text.strip()
                self.user_manager.save_user(user_id, user_data)
                await update.message.reply_text(
                    f"✅ Email сохранен: {text}\n\n"
                    f"Теперь укажите ваш часовой пояс.\n"
                    f"Вы можете ввести:\n"
                    f"- смещение относительно UTC, например +3 или -5\n"
                    f"- название города, например Moscow, Bangkok"
                )
                context.user_data['waiting_for'] = 'timezone'
            else:
                await update.message.reply_text("❌ Некорректный email, попробуйте снова:")

        elif waiting_for == 'timezone':
            tz = parse_timezone(text)
            if tz:
                user_data = self.user_manager.get_user(user_id)
                user_data['timezone'] = tz

                if not user_data.get('calendar_id'):
                    # Пытаемся получить существующий календарь
                    existing_calendar_id = self.calendar_manager.get_user_calendar(user_data['email'])
                    if existing_calendar_id:
                        calendar_id = existing_calendar_id
                    else:
                        # Если нет — создаем новый
                        calendar_id = self.calendar_manager.create_user_calendar(
                            user_email=user_data['email'],
                            user_timezone=tz,
                            calendar_summary=f"{update.effective_user.first_name} Календарь"
                        )
                    user_data['calendar_id'] = calendar_id
                self.user_manager.save_user(user_id, user_data)

                await update.message.reply_text(
                    f"✅ Часовой пояс сохранен: {tz}\n\n"
                    f"За сколько минут до события присылать напоминание? (например: 10):"
                )
                context.user_data['waiting_for'] = 'reminder'
            else:
                await update.message.reply_text(

                    "❌ Некорректный часовой пояс.\n"
                    "Вы можете ввести:\n"
                    "- смещение относительно UTC, например +3 или -5\n"
                    "- название города, например Moscow, Bangkok\n\n"
                    "Попробуйте еще раз:"
                )


        elif waiting_for == 'reminder':
            try:
                minutes = int(text.strip())
                if 1 <= minutes <= 1440:  # от 1 минуты до 24 часов
                    user_data = self.user_manager.get_user(user_id)
                    user_data['reminder_minutes'] = minutes
                    self.user_manager.save_user(user_id, user_data)

                    await update.message.reply_text(
                        f"✅ Настройка завершена!\n\n"
                        f"📧 Email: {user_data['email']}\n"
                        f"🌍 Часовой пояс: {user_data['timezone']}\n"
                        f"⏰ Напоминания: за {minutes} мин\n\n"
                        f"Теперь отправьте сообщение с датой и описанием события!"
                    )
                    del context.user_data['waiting_for']
                else:
                    await update.message.reply_text("❌ Укажите число от 1 до 1440 минут:")
            except ValueError:
                await update.message.reply_text("❌ Укажите число (количество минут):")

    @staticmethod
    async def schedule_reminder(chat_id: int, event_title: str, event_datetime: datetime, reminder_datetime: datetime,
                                context, location: str = None, description: str = None):
        now = datetime.now(reminder_datetime.tzinfo)
        if reminder_datetime <= now:
            return
        delay = (reminder_datetime - now).total_seconds()

        async def send_reminder():
            await asyncio.sleep(delay)
            message = (
                f"⏰ Напоминание!\n"
                f"📅 {event_title}\n"
                f"🕐 {event_datetime.strftime('%d.%m.%Y %H:%M')}"
            )
            if location:
                message += f"\n📍 {location}"
            if description:
                message += f"\n📝 {description}"

            await context.bot.send_message(chat_id=chat_id, text=message)

        asyncio.create_task(send_reminder())

    def run(self):
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler('email', self.handle_email_command))
        app.add_handler(CommandHandler('timezone', self.handle_timezone_command))
        app.add_handler(CommandHandler('alert', self.handle_alert_command))
        app.add_handler(CommandHandler("schedule", self.handle_schedule_command))
        app.add_handler(CommandHandler("calendar", self.handle_calendar_command))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("Бот запущен!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

# ---------------- ЗАПУСК ----------------
if __name__ == '__main__':
    bot = TelegramCalendarBot()
    bot.run()
