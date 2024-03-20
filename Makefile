.PHONY: default
default: run

.PHONY: run
run:
	@echo "Starting server.py with uvicorn..."
	@pip install fastapi uvicorn
	@uvicorn server:app --reload