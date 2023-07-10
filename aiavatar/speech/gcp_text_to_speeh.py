import asyncio
import io
from logging import getLogger, NullHandler
import traceback
import wave
import numpy
import sounddevice
from .speech_controller import SpeechController
from google.cloud import texttospeech

class VoiceClip:
    def __init__(self, text: str):
        self.text = text
        self.download_task = None
        self.audio_clip = None


class GCPTextToSpeechController(SpeechController):
    def __init__(self, voice_selection_params: texttospeech.VoiceSelectionParams, audio_config: texttospeech.AudioConfig, device_index: int=-1):
        self.logger = getLogger(__name__)
        self.logger.addHandler(NullHandler())

        self.client = texttospeech.TextToSpeechClient()
        self.voice_selection_params = voice_selection_params
        self.audio_config = audio_config
        self.device_index = device_index

        self.voice_clips = {}
        self._is_speaking = False

    async def download(self, voice: VoiceClip):
        synthesis_input = texttospeech.SynthesisInput(text=voice.text)
        response = self.client.synthesize_speech(
            input=synthesis_input, voice=self.voice_selection_params, audio_config=self.audio_config
        )
        voice.audio_clip = response.audio_content

    def prefetch(self, text: str):
        v = self.voice_clips.get(text)
        if v:
            return v
        
        v = VoiceClip(text)
        v.download_task = asyncio.create_task(self.download(v))       
        self.voice_clips[text] = v
        return v

    async def speak(self, text: str):
        voice = self.prefetch(text)
        
        if not voice.audio_clip:
            await voice.download_task
        
        with wave.open(io.BytesIO(voice.audio_clip), "rb") as f:
            try:
                self._is_speaking = True
                data = numpy.frombuffer(
                    f.readframes(f.getnframes()),
                    dtype=numpy.int16
                )
                sounddevice.play(data, f.getframerate(), device=self.device_index)
                sounddevice.wait()

            except Exception as ex:
                self.logger.error(f"Error at speaking: {str(ex)}\n{traceback.format_exc()}")

            finally:
                self._is_speaking = False

    def is_speaking(self) -> bool:
        return self._is_speaking
