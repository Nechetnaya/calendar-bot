## Настройка Service Account для Google Calendar с индивидуальными календарями пользователей


### 1. Создание Service Account

- Перейдите в [Google Cloud Console](https://console.cloud.google.com/)

- Создайте новый проект или выберите существующий.

- Включите Google Calendar API:
  - "APIs & Services" → "Library"
  - Найдите "Google Calendar API" → включите.

- Создайте Service Account:

   - "APIs & Services" → "Credentials" → "Create Credentials" → "Service Account"

   - Заполните имя и описание → "Create and Continue".

- Скачайте JSON ключ:

   - В Service Account → вкладка "Keys" → "Add Key" → "Create new key"

   - Выберите формат JSON → сохраните как service-account-credentials.json.

### 2. Логика работы с календарями пользователей

- Для каждого нового пользователя бот создаёт новый календарь под сервисным аккаунтом.

- После создания календаря бот даёт пользователю доступ на запись (role: writer).

- События создаются уже в личном календаре пользователя, не в общем сервисном календаре.

- При этом Service Account имеет полный доступ ко всем календарям, чтобы управлять событиями.

⚠️ `Не нужно вручную делиться календарём с пользователем — бот делает это автоматически через API.`

### 3. Настройка проекта

- Поместите service-account-credentials.json в папку с ботом.

- В google_calendar_manager.py укажите путь к JSON файлу и используйте методы для:

   - создания календаря (service.calendars().insert(...))

   - выдачи доступа пользователю (service.acl().insert(...)).

- Установите зависимости:   
`pip install -r requirements.txt`

- Создайте .env файл и добавьте Telegram токен:  
`TELEGRAM_BOT_TOKEN=ваш_токен`

### 4. Запуск бота   
 -  `python run.py` 
