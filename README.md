# DataVoice: Your Interactive Voice Assistant

DataVoice is an innovative project designed to bridge the gap between you and data analysis through voice commands. Using a blend of AI models and a user-friendly chat interface, DataVoice allows you to navigate and perform actions on your computer with ease.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, make sure you have the following installed:
- [Docker](https://www.docker.com/get-started) (required for running the MongoDB container)
- [Node.js](https://nodejs.org/en/) (required for the chat-UI)
- [Python](https://www.python.org/) version 3.8 or higher

### Installation

1. **Clone the repository**

    ```
    git clone https://github.com/wizapp-link/DataVoice.git
    cd DataVoice
    ```

2. **API Keys Setup**

    You need to provide your API keys in `.env.local` files located at the project root and within the `chat-ui` directory. The file should look something like this:

    ```
    ELEVEN_LABS_API_KEY=your_eleven_labs_api_key_here
    OPENAI_API_KEY=your_openai_api_key_here
    OPENAI_WHISPER_MODEL=your_whisper_model_name_here
    ```

### Running DataVoice

3. **Open Two Terminals**

    Open two terminals on your computer. In one terminal, navigate to the project root. In the other, navigate to the `chat-ui` directory within the project.

    ```
    # Terminal 1 - Project Root
    cd path/to/DataVoice

    # Terminal 2 - Chat-UI
    cd path/to/DataVoice/chat-ui
    ```

4. **Start the Services**

    In both terminals, run the following command to start the respective services:

    ```
    make init
    make run
    ```

    This command will start the backend service in one terminal and the chat-UI service in the other.

5. **Accessing DataVoice**

    After starting the services, the chat-UI terminal will display a URL (e.g., `http://localhost:5173`). Open this URL in your web browser to access the DataVoice chat interface.

6. **Using DataVoice**

    In the chat interface:
    - Select "DataVoice" from the "Models" tab.
    - Type or speak a command into the chatbox, such as "Show me what's under the current working directory."

    DataVoice will process your request and respond accordingly.

## Troubleshooting

If you encounter any issues while running DataVoice, ensure that:
- Your API keys are correctly entered in the `.env.local` files.
- You have the required software installed and up to date.
- Docker is running if you are using a MongoDB container for the chat-UI.

For further assistance, please open an issue in the project repository.