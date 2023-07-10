import logging
from aiavatar import AIAvatar, WakewordListener
from aiavatar.device.audio import AudioDevice
from aiavatar.speech.gcp_text_to_speeh import GCPTextToSpeechController
from google.cloud import texttospeech

GOOGLE_API_KEY = "YOUR_API_KEY"
OPENAI_API_KEY = "YOUR_API_KEY"
VV_URL = "http://127.0.0.1:50021"
VV_SPEAKER = 46

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = logging.Formatter("[%(levelname)s] %(asctime)s : %(message)s")
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(log_format)
logger.addHandler(streamHandler)

# Prompt
system_message_content = """あなたは「joy」「angry」「sorrow」「fun」の4つの表情を持っています。
特に表情を表現したい場合は、文章の先頭に[face:joy]のように挿入してください。

例
[face:joy]ねえ、海が見えるよ！[face:fun]早く泳ごうよ。
"""

# Create Speech Controller
voice = texttospeech.VoiceSelectionParams(
        name="en-US-Neural2-G",
        language_code="en-US",
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16
)

output_device = -1
if isinstance(output_device, int):
    if output_device < 0:
        output_device_info = AudioDevice.get_default_output_device_info()
        output_device = output_device_info["index"]
    else:
        output_device_info = AudioDevice.get_device_info(output_device)
elif isinstance(output_device, str):
    output_device_info = AudioDevice.get_output_device_by_name(output_device)
    if output_device_info is None:
        output_device_info = AudioDevice.get_default_output_device_info()
    output_device = output_device_info["index"]

logger.info(f"Output device: [{output_device}] {output_device_info['name']}")

speech_controller = GCPTextToSpeechController(
    voice_selection_params=voice,
    audio_config=audio_config,
    device_index=output_device,
)

# Create AIAvatar
app = AIAvatar(
    google_api_key=GOOGLE_API_KEY,
    openai_api_key=OPENAI_API_KEY,
    speech_controller=speech_controller,
    system_message_content=system_message_content,
)

# Create WakewordListener
wakewords = ["こんにちは"]

async def on_wakeword(text):
    logger.info(f"Wakeword: {text}")
    await app.start_chat()

wakeword_listener = WakewordListener(
    api_key=GOOGLE_API_KEY,
    wakewords=wakewords,
    on_wakeword=on_wakeword,
    device_index=app.input_device
)

# Start listening
ww_thread = wakeword_listener.start()
ww_thread.join()
