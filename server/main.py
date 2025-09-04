import os

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse


app = FastAPI()


static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
def root(request: Request):
    query = request.url.query  # получаем все query-параметры
    return RedirectResponse(f"/static/index.html?{query}" if query else "/static/index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Авторизация через сервисный аккаунт
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "../credentials.json")


credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
calendar = build("calendar", "v3", credentials=credentials)


# в аргументах функции добавьте:
# start: str = Query(None, description="ISO start date, например 2025-08-25"),
# end: str = Query(None, description="ISO end date, например 2025-10-05")

@app.get("/api/calendar")
def get_calendar(
    cid: str = Query(..., description="Calendar ID"),
    mode: str = Query("month", description="day | week | month"),
    date: str = Query(None, description="ISO date (например 2025-09-03)"),
    start: str = Query(None, description="ISO start date override"),
    end: str = Query(None, description="ISO end date override")
):
    try:
        if start and end:
            time_min = datetime.fromisoformat(start)
            time_max = datetime.fromisoformat(end)
        else:
            base_date = datetime.fromisoformat(date) if date else datetime.utcnow()

            if mode == "day":
                time_min = base_date
                time_max = base_date + timedelta(days=1)
            elif mode == "week":
                start_week = base_date - timedelta(days=(base_date.weekday()))
                time_min = start_week
                time_max = start_week + timedelta(days=7)
            else:  # month
                start_month = base_date.replace(day=1)
                if start_month.month == 12:
                    end_month = start_month.replace(year=start_month.year + 1, month=1, day=1)
                else:
                    end_month = start_month.replace(month=start_month.month + 1, day=1)
                time_min, time_max = start_month, end_month

        events_result = calendar.events().list(
            calendarId=cid,
            timeMin=time_min.isoformat() + "Z",
            timeMax=time_max.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return {"events": events_result.get("items", [])}
    except Exception as e:
        return {"error": str(e)}



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
