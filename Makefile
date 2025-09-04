.PHONY: run, app
# auto reload
run:
	.venv/bin/watchmedo auto-restart --patterns="*.py" --recursive -- python run.py

app:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000
