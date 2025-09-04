# Telegram Calendar Bot G-Buddy

**Overview:**  
Telegram bot designed to intelligently recognize events from natural language messages, create them in Google Calendar, and provide answers to scheduling queries. 

In future updates, it will support OCR for extracting events from screenshots.

---

## Key Features

- **Smart Event Recognition:** Extracts date, time, duration, title, and location from user messages.  
- **Google Calendar Integration:** Creates and synchronizes events seamlessly.  
- **User Confirmation:** Ensures events are only added after user approval.  
- **Schedule Queries:** Users can ask about planned events or available free time.  
- **Mini Calendar Web App:** FastAPI-based interface displaying Month / Week / Day views.  

---

## Technologies

- **Python 3.11**  
- [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)  
- **Google Calendar API**  
- **dateparser + regex** for text parsing  
- **pytz** for timezone management  
- **FastAPI + Uvicorn** for the mini calendar web app  
- **OpenAI API (ChatGPT-5 Nano)** for NLP event extraction  

---

## Running the Application

### FastAPI App
uvicorn server.main:app --host 0.0.0.0 --port 8000

### Telegram Bot
python run.py

## Example Bot Interaction

**User:**  
Tomorrow meeting with Ann at 14:30 MSK

**Bot:**  
Do you want to create an event?  
📅 Meeting with Ann  
🗓 22.08.2025  
⏰ 14:30 — 15:30  
📍 MSK  
[✅ Yes] [❌ No]

**User:**  
✅ Yes

**Bot:**  
✅ Event created!  
📅 Meeting with Ann  
🕐 22.08.2025 14:30  
📍 MSK  

**Schedule query:**  
Tell me what is planned for today

**Bot:**  
22.08.2025:  
14:30 — 15:30: Meeting with Ann (MSK)

