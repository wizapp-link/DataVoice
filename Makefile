# Name of the virtual environment
VENV := datavoice_venv

# Default Python interpreter
PYTHON := python3

# Command to create the virtual environment
init:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created."

# Command to install dependencies
install: init ffmpeg_install
	@echo "Installing dependencies..."
	./$(VENV)/bin/pip install -r requirements.txt
	@echo "Installing Whisper from GitHub..."
	./$(VENV)/bin/pip install git+https://github.com/openai/whisper.git
	@echo "Dependencies installed."

# Command to install ffmpeg
ffmpeg_install:
	@echo "Installing ffmpeg..."
	sudo apt-get update
	sudo apt-get install -y ffmpeg
	@echo "ffmpeg installed."

# Command to activate the virtual environment (Note: This has limitations in Makefile)
activate:
	@echo "To activate the virtual environment, run 'source $(VENV)/bin/activate'"

# Optionally, you can add a command to run your application
run:
	./$(VENV)/bin/python app.py

# Clean up command to remove the virtual environment
clean:
	rm -rf $(VENV)
	@echo "Cleaned up the virtual environment."

.PHONY: init install activate run clean
