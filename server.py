import asyncio
import json
import time
from typing import Dict, List
import uuid
import logging
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import shutil
from pathlib import Path

# Define the path to the assistant_workdir sub-folder
workdir_path = os.path.join(os.getcwd(), "assistant_workdir")

# change the current working directory to assistant_workdir
os.chdir(workdir_path)

from interpreter import interpreter

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    temperature: float = 1.0
    max_tokens: int = None


# Load the environment variables from .env.local file
load_dotenv(dotenv_path='../env.local')

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



app.mount("/static", StaticFiles(directory=workdir_path), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Disable open-interpreter's history preserving feature
interpreter.conversation_history = False

# Add interpreter system message
interpreter.system_message += """
To display ANY images in UI, save visualizations as PNG in the 'images' directory. Then, reference them with markdown: ![](http://localhost:8000/static/images/<imageName>.png). Do this directly in PLAIN ASSISTANT TEXT, WITHOUT ANY BLOCK FORMATTING.
"""
print(interpreter.system_message)

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
                
        # Fetch the last fetched knowledge content
        knowledge_content = await get_last_fetched_knowledge_content(workdir_path)
        # # Append the "Knowledge Base" role and content
        # open_interpreter_messages.append({"role": "Some Facts", "content": knowledge_content})
        # Calculate the insertion index for second last position
        insertion_index = len(open_interpreter_messages) - 1
        # Insert the "Knowledge Base" role and content at the second last index
        open_interpreter_messages.insert(insertion_index, {"role": "User Hints", "content": knowledge_content})



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

@app.get("/knowledge")
async def get_knowledge(conversation_id: str = Query(None, alias="conversationId")):
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Missing conversationId")
    
    knowledge_dir = os.path.join(workdir_path, ".assistant", "knowledge")
    knowledge_file_path = os.path.join(knowledge_dir, f"{conversation_id}")
    default_file_path = os.path.join(knowledge_dir, "default")
    last_fetched_id_path = os.path.join(knowledge_dir, "lastFetchedId")

    # Ensure the knowledge directory exists
    os.makedirs(knowledge_dir, exist_ok=True)

    try:
        try:
            # Try to open the specified conversationId file
            with open(knowledge_file_path, "r") as file:
                content = file.read()
        except FileNotFoundError:
            # If the file does not exist, create it with content from the default file
            with open(default_file_path, "r") as default_file:
                default_content = default_file.read()
            with open(knowledge_file_path, "w") as new_file:
                new_file.write(default_content)
            content = default_content
        
        # Update lastFetchedId with the current conversation_id
        with open(last_fetched_id_path, "w") as last_fetched_file:
            last_fetched_file.write(conversation_id)

        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@app.post("/knowledge")
async def save_knowledge(request: Request):
    data = await request.json()
    
    # Extract conversationID and content from the request
    conversation_id = data.get("conversationId")
    content = data.get("content")
    
    if not conversation_id or content is None:
        raise HTTPException(status_code=400, detail="Missing conversationID or content in the request body")
    
    # Define the directory and file path based on conversationID
    knowledge_dir = os.path.join(workdir_path, ".assistant", "knowledge")
    file_path = os.path.join(knowledge_dir, f"{conversation_id}")
    
    # Ensure the directory exists
    os.makedirs(knowledge_dir, exist_ok=True)
    
    # Write content to the file
    try:
        with open(file_path, "w") as file:
            file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"status": "success", "message": f"Content saved for conversationID: {conversation_id}"}


async def get_last_fetched_knowledge_content(workdir_path: str) -> str:
    knowledge_dir = os.path.join(workdir_path, ".assistant", "knowledge")
    last_fetched_id_path = os.path.join(knowledge_dir, "lastFetchedId")
    
    # Read the last fetched ID
    try:
        with open(last_fetched_id_path, "r") as file:
            last_fetched_id = file.read().strip()
    except FileNotFoundError:
        knowledge_content = ""
    
    # Fetch the knowledge content for the last fetched ID
    knowledge_file_path = os.path.join(knowledge_dir, last_fetched_id)
    try:
        with open(knowledge_file_path, "r") as file:
            knowledge_content = file.read()
    except FileNotFoundError:
        knowledge_content = ""  # Consider a default behavior if the knowledge file doesn't exist
    
    return knowledge_content


ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.json', '.txt', '.parquet'}

@app.post("/upload-file/")
async def upload_file(file: UploadFile = File(...)):
    upload_dir = Path(workdir_path)
    
    if any(file.filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        file_location = upload_dir / file.filename
        with file_location.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    else:
        return JSONResponse(status_code=400, content={"message": "File type not allowed, we accept '.csv', '.xlsx', '.json', '.txt', '.parquet' files."})

    return JSONResponse(status_code=200, content={"message": f"File '{file.filename}' uploaded successfully."})



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)