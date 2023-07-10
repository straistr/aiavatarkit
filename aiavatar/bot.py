import asyncio
from logging import getLogger, NullHandler
import traceback
from typing import Callable
# Device
from .device import AudioDevice
# Processor
from .processors.chatgpt import ChatGPTProcessor
# Listener
from .listeners.voicerequest import VoiceRequestListener
# Avatar
from .speech.speech_controller import SpeechController
from .animation import AnimationController, AnimationControllerDummy
from .face import FaceController, FaceControllerDummy
from .avatar import AvatarController

class AIAvatar:
    def __init__(
        self,
        google_api_key: str,
        openai_api_key: str,
        speech_controller: SpeechController,
        volume_threshold: int=3000,
        start_voice: str="どうしたの",
        functions: dict=None,
        system_message_content: str=None,
        animation_controller: AnimationController=None,
        face_controller: FaceController=None,
        avatar_request_parser: Callable=None,
        input_device: int=-1,
        output_device: int=-1
    ):

        self.logger = getLogger(__name__)
        # self.logger.addHandler(NullHandler())

        self.google_api_key = google_api_key
        self.openai_api_key = openai_api_key
        self.volume_threshold = volume_threshold

        # Audio Devices
        if isinstance(input_device, int):
            if input_device < 0:
                input_device_info = AudioDevice.get_default_input_device_info()
                input_device = input_device_info["index"]
            else:
                input_device_info = AudioDevice.get_device_info(input_device)
        elif isinstance(input_device, str):
            input_device_info = AudioDevice.get_input_device_by_name(input_device)
            if input_device_info is None:
                input_device_info = AudioDevice.get_default_input_device_info()
            input_device = input_device_info["index"]

        self.input_device = input_device
        self.logger.info(f"Input device: [{input_device}] {input_device_info['name']}")

        # Processor
        self.chat_processor = ChatGPTProcessor(self.openai_api_key, functions=functions, system_message_content=system_message_content)

        # Listeners
        self.request_listener = VoiceRequestListener(self.google_api_key, volume_threshold=volume_threshold, device_index=self.input_device)

        # Avatar
        animation_controller = animation_controller or AnimationControllerDummy()
        face_controller = face_controller or FaceControllerDummy()
        self.avatar_controller = AvatarController(speech_controller, animation_controller, face_controller, avatar_request_parser)

        # Chat
        self.chat_task = None
        self.start_voice = start_voice

    async def chat(self, request_on_start: str=None, skip_start_voice: bool=False):
        if not skip_start_voice:
            try:
                await self.avatar_controller.speech_controller.speak(self.start_voice)
            except Exception as ex:
                self.logger.error(f"Error at starting chat: {str(ex)}\n{traceback.format_exc()}")

        while True:
            try:
                if request_on_start:
                    req = request_on_start
                    request_on_start = None
                else:
                    req = await self.request_listener.get_request()
                    if not req:
                        break

                self.logger.info(f"User: {req}")
                self.logger.info("AI:")

                avatar_task = asyncio.create_task(self.avatar_controller.start())

                stream_buffer = ""
                async for t in self.chat_processor.chat(req):
                    stream_buffer += t
                    sp = stream_buffer.replace("。", "。|").replace("、", "、|").replace("！", "！|").replace("？", "？|").split("|")
                    if len(sp) > 1: # >1 means `|` is found (splited at the end of sentence)
                        sentence = sp.pop(0)
                        stream_buffer = "".join(sp)
                        self.avatar_controller.set_text(sentence)

                self.avatar_controller.set_stop()
                await avatar_task
            
            except Exception as ex:
                self.logger.error(f"Error at chatting loop: {str(ex)}\n{traceback.format_exc()}")

    async def start_chat(self, request_on_start: str=None, skip_start_voice: bool=False):
        self.stop_chat()
        self.chat_task = asyncio.create_task(self.chat(request_on_start, skip_start_voice))
        await self.chat_task

    def stop_chat(self):
        if self.chat_task is not None:
            self.chat_task.cancel()
