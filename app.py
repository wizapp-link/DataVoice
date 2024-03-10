import os
from dotenv import load_dotenv
import gradio as gr
import time
from interpreter import interpreter
import whisper
from elevenlabs import generate, play, set_api_key
import io
from pydub import AudioSegment

# Load the environment variables from .env.local file
load_dotenv(dotenv_path='.env.local')

# Retrieve config from .env.local
eleven_labs_api_key = os.getenv("ELEVEN_LABS_API_KEY")
openai_whisper_model_name = os.getenv("OPENAI_WHISPER_MODEL")

## Open Interpreter
# interpreter.auto_run = True

# Run with local LLM
interpreter.offline = True # Disables online features like Open Procedures
interpreter.llm.model = "ollama_chat/mistral"
interpreter.llm.api_base = "http://localhost:11434"

# Run with OpenAI GPT-4 (COSTY!)
# openai_api_key = os.getenv("OPENAI_API_KEY")
# interpreter.llm.api_key = openai_api_key

# TODO: Run with LLM hosted at an API endpoint
# interpreter.llm.model = "ollama_chat/mistral"
# interpreter.llm.api_base = "http://192.168.2.12:11434"


def transcribe(audio):
    # Load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio)
    audio = whisper.pad_or_trim(audio)

    # Make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    
    # detect the spoken language
    _, probs = model.detect_language(mel)

    # Detect the spoken language and decode the audio
    options = whisper.DecodingOptions()
    result = whisper.decode(model, mel, options)
    return result.text

### ElevenLabs
set_api_key(eleven_labs_api_key)

def get_audio_length(audio_bytes):
    byte_io = io.BytesIO(audio_bytes)
    audio = AudioSegment.from_mp3(byte_io)
    length_ms = len(audio)
    length_s = length_ms / 1000.0
    return length_s

def speak(text):
    speaking = True
    audio = generate(
        text=text,
        voice="Daniel"
    )
    play(audio)

    audio_length = get_audio_length(audio)
    time.sleep(audio_length)

def transcribe(audio):
    audio = whisper.load_audio(audio)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)
    options = whisper.DecodingOptions()
    result = whisper.decode(model, mel, options)
    return result.text

def add_user_message(audio, history):
    user_message = transcribe(audio)
    return history + [[user_message, None]]

def bot(history):
    global last_sentence
    if not history:  # Check if history is empty
        return "", []  # Return empty history if there's nothing to process

    user_message = history[-1][0]
    history[-1][1] = ""
    active_block_type = ""
    language = ""
    for chunk in interpreter.chat(user_message, stream=True, display=True):

        # Message
        if chunk["type"] == "message" and "content" in chunk:
            if active_block_type != "message":
                active_block_type = "message"
            history[-1][1] += chunk["content"]

            last_sentence += chunk["content"]
            if any([punct in last_sentence for punct in ".?!\n"]):
                yield history
                speak(last_sentence)
                last_sentence = ""
            else:
                yield history

        # Code
        if chunk["type"] == "code" and "content" in chunk:
            if active_block_type != "code":
                active_block_type = "code"
                history[-1][1] += f"\n```{chunk['format']}"
            history[-1][1] += chunk["content"]
            yield history

        # Output
        if chunk["type"] == "confirmation":
            history[-1][1] += "\n```\n\n```text\n"
            yield history
        if chunk["type"] == "console":
            if chunk.get("format") == "output":
                if chunk["content"] == "KeyboardInterrupt":
                    break
                history[-1][1] += chunk["content"] + "\n"
                yield history
            if chunk.get("format") == "active_line" and chunk["content"] == None:
                # Active line will be none when we finish execution.
                # You could also detect this with "type": "console", "end": True.
                history[-1][1] = history[-1][1].strip()
                history[-1][1] += "\n```\n"
                yield history

    if last_sentence:
        speak(last_sentence)


with gr.Blocks() as demo:

    chatbot = gr.Chatbot()
    audio_input = gr.inputs.Audio(source="microphone", type="filepath")
    btn = gr.Button("Submit")

    btn.click(add_user_message, [audio_input, chatbot], [chatbot]).then(
        bot, chatbot, chatbot
    )


if __name__ == "__main__":
    model = whisper.load_model(openai_whisper_model_name)
    last_sentence = ""
    demo.queue()
    demo.launch(debug=True)