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

    async def create_event(
            self,
            title,
            start_datetime,
            end_datetime: Optional[datetime] = None,
            timezone='Europe/Moscow',
            calendar_id=None
    ) -> str:
        """Создание события в календаре пользователя"""
        calendar_id = calendar_id or self.calendar_id
        try:
            if end_datetime is None:
                end_datetime = start_datetime + timedelta(hours=1)

            event = {
                'summary': title,
                'description': 'Создано через Telegram бота',
                'start': {'dateTime': start_datetime.isoformat(), 'timeZone': timezone},
                'end': {'dateTime': end_datetime.isoformat(), 'timeZone': timezone},
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 10},
                        {'method': 'popup', 'minutes': 10},
                    ],
                }
            }

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            event_link = created_event.get('htmlLink')
            logger.info(f"Событие '{title}' создано в календаре {calendar_id}")
            return event_link

        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}")
            return None

    def list_upcoming_events(self, calendar_id: str, max_results: int = 10) -> list:
        """Получение предстоящих событий для конкретного календаря"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])
        except Exception as e:
            logger.error(f"Ошибка при получении событий: {e}")
            return []
