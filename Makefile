.PHONY: run
# auto reload
run:
	.venv/bin/watchmedo auto-restart --patterns="*.py" --recursive -- python run.py
