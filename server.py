import asyncio
import json
import time
from typing import Dict, List
import uuid
import logging
import os
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from interpreter import interpreter

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 1.0
    max_tokens: int = None


# Load the environment variables from .env.local file
load_dotenv(dotenv_path='.env.local')

# Retrieve config from .env.local
eleven_labs_api_key = os.getenv("ELEVEN_LABS_API_KEY")
openai_whisper_model_name = os.getenv("OPENAI_WHISPER_MODEL")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set or replace the environment variables for the current process
os.environ["ELEVEN_LABS_API_KEY"] = eleven_labs_api_key
os.environ["OPENAI_WHISPER_MODEL"] = openai_whisper_model_name
os.environ["OPENAI_API_KEY"] = openai_api_key

app = FastAPI()
interpreter.llm.model = "gpt-3.5-turbo"
interpreter.llm.api_key = openai_api_key
interpreter.auto_run = True

# Define the path to the assistant_workdir sub-folder
workdir_path = os.path.join(os.getcwd(), "assistant_workdir")

# change the current working directory to assistant_workdir
os.chdir(workdir_path)

# Disable open-interpreter's history preserving feature
interpreter.conversation_history = False

# Set up logging
logging.basicConfig(filename='open_interpreter_response.log', level=logging.INFO)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, chat_request: ChatCompletionRequest):
    # Log the incoming messages
    print("Incoming messages:")
    for message in chat_request.messages:
        print(f"Role: {message['role']}, Content: {message['content']}")

    async def event_stream():
        # Convert Chat-UI messages to open-interpreter format
        open_interpreter_messages = []
        for message in chat_request.messages:
            if message["role"] == "user":
                open_interpreter_messages.append({"role": "user", "content": message["content"]})
            elif message["role"] == "assistant":
                open_interpreter_messages.append({"role": "assistant", "content": message["content"]})

        completion_id = str(uuid.uuid4())
        completion_object = {
            "id": f"chatcmpl-{completion_id}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": chat_request.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "logprobs": None,
                    "finish_reason": None
                }
            ],
        }

        # Join the open_interpreter_messages into a single string
        open_interpreter_input = "\n".join([f"{msg['role']}: {msg['content']}" for msg in open_interpreter_messages])

        print(f"Message sent to open-interpreter:\n>>>>>\n{open_interpreter_input}")
        
        # Get the open-interpreter response as a complete JSON object
        open_interpreter_response = interpreter.chat(open_interpreter_input, stream=False)
        
        # Log the entire open-interpreter response
        logging.info(f"Open-interpreter response:\n{json.dumps(open_interpreter_response)}")
        
        content = ""
        for chunk in open_interpreter_response:
            if chunk["role"] == "assistant" and chunk["type"] == "message":
                content += chunk["content"]
            elif chunk["role"] == "user":
                pass
            else:
                tag = f"```{chunk['format']}\n" if chunk["type"] == "code" else f"```{chunk['type']}\n"
                content += f"\n{tag}{chunk['content']}\n```\n"

        completion_object["choices"][0]["delta"]["content"] = content
        completion_object["choices"][0]["finish_reason"] = "stop"
        yield f"data: {json.dumps(completion_object)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)