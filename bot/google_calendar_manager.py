import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleCalendarManager:
    def __init__(self):
        self.service = None
        self._setup_service_account()

    def _setup_service_account(self):
        """Настройка Service Account для доступа к календарю"""
        try:
            service_account_file = 'credentials.json'
            if not os.path.exists(service_account_file):
                raise FileNotFoundError(f"Файл {service_account_file} не найден")

            scopes = ['https://www.googleapis.com/auth/calendar']
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=scopes
            )
            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Service Account успешно настроен")
        except Exception as e:
            logger.error(f"Ошибка настройки Service Account: {e}")
            raise

    def create_user_calendar(self, user_email: str,  user_timezone: str,
                             calendar_summary: str = "Calendar_bot") -> str:
        """Создаём отдельный календарь для пользователя и даём права на запись"""
        try:
            # Создаём календарь
            calendar = {
                'summary': calendar_summary,
                'timeZone':  user_timezone
            }
            created_calendar = self.service.calendars().insert(body=calendar).execute()
            calendar_id = created_calendar['id']

            # Даем пользователю права на запись
            acl_rule = {
                'role': 'writer',  # можно writer/editor
                'scope': {'type': 'user', 'value': user_email}
            }
            self.service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
            logger.info(f"Календарь создан для {user_email}, "
                        f"calendarId={calendar_id}, "
                        f"timezone={user_timezone}")

            return calendar_id
        except HttpError as error:
            logger.error(f"HTTP ошибка при создании календаря: {error}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании календаря: {e}")
            return None

    def create_event(
            self,
            user_calendar_id: str,
            start: datetime,
            end: datetime = None,
            title: str = None,
            location: str = None,
            description: str = None,
            timezone: str = "Europe/Moscow"
    ) -> str:
        """Создание события в календаре пользователя"""
        try:
            # если конец не указан — +1 час
            if end is None:
                end = start + timedelta(hours=1)

            event = {
                'summary': title if title else "Без названия",
                'location': location if location else None,
                'description': description if description else None,
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': timezone
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': timezone
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 10},
                        {'method': 'popup', 'minutes': 10},
                    ],
                }
            }

            created_event = self.service.events().insert(
                calendarId=user_calendar_id,
                body=event
            ).execute()

            event_link = created_event.get('htmlLink')
            logger.info(f"Событие '{title}' создано в календаре {user_calendar_id}")
            return event_link

        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}")
            return None


    def get_events(self, user_calendar_id: str, time_min: datetime, time_max: datetime):
        """
        Возвращает список событий из календаря за указанный период
        :param user_calendar_id: id календаря пользователя
        :param time_min: datetime начала диапазона
        :param time_max: datetime конца диапазона
        :return: список словарей с ключами 'title', 'start', 'end'
        """
        if not user_calendar_id:
            return []

        # Приведение к формату ISO
        time_min_iso = time_min.isoformat()
        time_max_iso = time_max.isoformat()

        try:
            events_result = self.service.events().list(
                calendarId=user_calendar_id,
                timeMin=time_min_iso,
                timeMax=time_max_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = []
            for e in events_result.get('items', []):
                start = e['start'].get('dateTime') or e['start'].get('date')
                end = e['end'].get('dateTime') or e['end'].get('date')

                # Конвертация строк в datetime с учетом часового пояса
                from dateutil.parser import parse
                start_dt = parse(start)
                end_dt = parse(end) if end else None

                events.append({
                    'title': e.get('summary', 'Без названия'),
                    'start': start_dt,
                    'end': end_dt
                })

            return events

        except Exception as ex:
            logging.getLogger(__name__).error(f"Ошибка при получении событий: {ex}")
            return []

    def get_free_slots(
            self, user_calendar_id: str, time_min: datetime, time_max: datetime
    ):
        """
        Возвращает список слотов по 1 часу с отметкой свободен/занят.
        :return: [{'start': datetime, 'end': datetime, 'free': True/False}]
        """
        events = self.get_events(user_calendar_id, time_min, time_max)
        events = sorted(events, key=lambda e: e['start'])
        slots = []

        current = time_min.replace(minute=0, second=0, microsecond=0)

        while current < time_max:
            slot_end = current + timedelta(hours=1)
            # проверяем, пересекается ли слот с каким-либо событием
            is_free = True
            for event in events:
                event_start = event['start']
                event_end = event['end'] or (event_start + timedelta(hours=1))
                if event_end > current and event_start < slot_end:
                    is_free = False
                    break

            slots.append({
                'start': current,
                'end': slot_end,
                'free': is_free
            })

            current = slot_end

        return slots

