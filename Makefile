# Name of the virtual environment
VENV := datavoice_venv

# Default Python interpreter
PYTHON := python3

# Default host and port for uvicorn
HOST := 0.0.0.0
PORT := 8000

.PHONY: default
default: run

# Command to create the virtual environment
init:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created."

# Command to install ffmpeg
ffmpeg_install:
	@echo "Installing ffmpeg..."
	sudo apt-get update
	sudo apt-get install -y ffmpeg
	@echo "ffmpeg installed."

# Command to install OpenAI Whisper
openai_whisper_install:
	@echo "Installing Whisper from GitHub..."
	./$(VENV)/bin/pip install git+https://github.com/openai/whisper.git

# Command to install dependencies
install: init
	@echo "Installing dependencies..."
	./$(VENV)/bin/pip install -r requirements.txt
	# Here include the installation of any other packages not available in PyPI
	@echo "Dependencies installed."

# Command to activate the virtual environment (Note: This command has limitations in Makefile)
activate:
	@echo "To activate the virtual environment, run 'source $(VENV)/bin/activate'"

# Command to run the application
run:
	@echo "Exporting environment variables from .env.local..."
	$(eval ELEVEN_LABS_API_KEY=$(shell grep ELEVEN_LABS_API_KEY .env.local | cut -d '=' -f2))
	$(eval OPENAI_API_KEY=$(shell grep OPENAI_API_KEY .env.local | cut -d '=' -f2))
	$(eval HUGGINGFACE_API_KEY=$(shell grep HUGGINGFACE_API_KEY .env.local | cut -d '=' -f2))
	$(eval OPENAI_WHISPER_MODEL=$(shell grep OPENAI_WHISPER_MODEL .env.local | cut -d '=' -f2))
	@export ELEVEN_LABS_API_KEY=$(ELEVEN_LABS_API_KEY) \
		OPENAI_API_KEY=$(OPENAI_API_KEY) \
		HUGGINGFACE_API_KEY=$(HUGGINGFACE_API_KEY) \
		OPENAI_WHISPER_MODEL=$(OPENAI_WHISPER_MODEL)
	@echo "Starting server.py with uvicorn..."
	./$(VENV)/bin/uvicorn server:app --reload --host $(HOST) --port $(PORT)


# Clean up command to remove the virtual environment
clean:
	rm -rf $(VENV)
	@echo "Cleaned up the virtual environment."