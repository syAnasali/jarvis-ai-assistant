"""Full-duplex Voice Pipeline orchestrating STT, AgentController, Sentence-level TTS, Barge-in, and Voice Approvals."""

import re
import time
from typing import Any, Dict, Generator, Iterable, Optional

from app.agent.controller import AgentController
from app.agent.models import AgentRequest
from app.approval.manager import ApprovalManager
from app.core.logger import JarvisLogger
from app.utils.id_generator import generate_request_id
from app.voice.interfaces import AudioCapture, SpeechToTextProvider, TextToSpeechProvider, VoiceActivityDetector, WakeWordDetector
from app.voice.models import AudioSegment, VoiceState
from app.voice.playback import PlaybackManager
from app.voice.session import VoiceSession

logger = JarvisLogger.get_logger("voice_pipeline")


def chunk_sentences(token_stream: Iterable[str]) -> Generator[str, None, None]:
    """Parses streaming LLM token chunks into sentence boundaries."""
    buffer = ""
    sentence_delimiters = re.compile(r'([.!?\n]+)')

    for chunk in token_stream:
        if not chunk:
            continue
        buffer += chunk
        
        # Split on sentence boundaries
        parts = sentence_delimiters.split(buffer)
        while len(parts) >= 3:
            sentence = parts.pop(0) + parts.pop(0)
            cleaned = sentence.strip()
            if cleaned:
                yield cleaned
        buffer = "".join(parts)

    if buffer.strip():
        yield buffer.strip()


class VoicePipeline:
    """Full-duplex voice interaction pipeline."""

    def __init__(
        self,
        stt_provider: SpeechToTextProvider,
        tts_provider: TextToSpeechProvider,
        vad_detector: VoiceActivityDetector,
        wakeword_detector: Optional[WakeWordDetector] = None,
        playback_manager: Optional[PlaybackManager] = None,
        approval_manager: Optional[ApprovalManager] = None,
        controller: Optional[AgentController] = None
    ) -> None:
        self.stt = stt_provider
        self.tts = tts_provider
        self.vad = vad_detector
        self.wakeword = wakeword_detector
        self.playback = playback_manager or PlaybackManager()
        self.approval_mgr = approval_manager
        self.controller = controller
        self.session: Optional[VoiceSession] = None
        self._running: bool = False

    def initialize(self) -> None:
        """Initializes all underlying provider resources."""
        logger.info("Initializing VoicePipeline resources...")
        self.stt.initialize()
        self.tts.initialize()
        if self.wakeword:
            self.wakeword.initialize()
        self.session = VoiceSession()
        self._running = True
        logger.info("VoicePipeline initialized successfully.")

    def process_utterance(self, segment: AudioSegment) -> Optional[str]:
        """Processes a single captured AudioSegment through STT, AgentController, sentence-level TTS, and approvals."""
        if not self.session:
            self.session = VoiceSession()

        # 1. Transcribe spoken audio
        self.session.transition_to(VoiceState.TRANSCRIBING)
        stt_result = self.stt.transcribe(segment)
        transcription_text = stt_result.text.strip()
        self.session.record_utterance(segment.duration_seconds)

        if not transcription_text:
            logger.info("Empty transcription output. Returning to LISTENING state.")
            self.session.transition_to(VoiceState.LISTENING)
            return None

        logger.info(f"Voice utterance transcribed: '{transcription_text}'")

        # 2. Check if answering a pending spoken approval
        if self.session.state == VoiceState.WAITING_APPROVAL and self.approval_mgr:
            return self._handle_spoken_approval_response(transcription_text)

        # 3. Agent Execution
        self.session.transition_to(VoiceState.PROCESSING)
        if not self.controller:
            logger.warning("No AgentController attached to VoicePipeline. Synthesizing direct echo.")
            self._speak_stream([f"You said: {transcription_text}"])
            self.session.transition_to(VoiceState.LISTENING)
            return f"You said: {transcription_text}"

        req = AgentRequest(request_id=generate_request_id(), text=transcription_text)
        stream = self.controller.process_request_stream(req)

        # 4. Sentence-level streaming TTS and playback
        self.session.transition_to(VoiceState.SPEAKING)
        sentences = chunk_sentences(stream)
        self._speak_stream(sentences)

        # 5. Check if execution was suspended for confirmation
        messages = self.controller.conversation.get_history()
        if messages:
            last_msg = messages[-1]
            if last_msg.role.value == "assistant" and last_msg.metadata.get("confirmation_required"):
                action_id = last_msg.metadata.get("pending_action_id")
                tool_name = last_msg.metadata.get("tool_name", "this action")
                self.session.transition_to(VoiceState.WAITING_APPROVAL)
                approval_prompt = f"I need your approval to execute {tool_name}. Please say yes to confirm or no to cancel."
                self.tts.speak(approval_prompt)
                return approval_prompt

        self.session.transition_to(VoiceState.LISTENING)
        return transcription_text

    def _speak_stream(self, sentence_stream: Iterable[str]) -> None:
        """Synthesizes and streams sentences to speaker while monitoring for barge-in."""
        for sentence in sentence_stream:
            if not self._running:
                break

            # Check if user barge-in interrupted playback
            if self.session and self.session.state == VoiceState.INTERRUPTED:
                logger.info("Barge-in active. Aborting remaining speech synthesis.")
                break

            # Synthesize & stream sentence
            audio_bytes_stream = self.tts.stream_speak([sentence])
            self.playback.stream_playback(audio_bytes_stream)

    def trigger_barge_in(self) -> None:
        """Triggers immediate barge-in interruption when user speaks during assistant playback."""
        logger.info("Barge-in triggered in VoicePipeline!")
        self.playback.interrupt(reason="Barge-in speech detected")
        if self.session:
            self.session.transition_to(VoiceState.INTERRUPTED)

    def _handle_spoken_approval_response(self, spoken_text: str) -> str:
        """Parses spoken approval response (yes/approve/confirm vs no/cancel/reject)."""
        lower = spoken_text.lower().strip()
        accept_words = ("yes", "approve", "confirm", "ok", "yep", "sure")
        reject_words = ("no", "cancel", "reject", "stop", "nope", "dont")

        messages = self.controller.conversation.get_history() if self.controller else []
        action_id = None
        if messages:
            last_msg = messages[-1]
            if last_msg.role.value == "assistant" and last_msg.metadata.get("confirmation_required"):
                action_id = last_msg.metadata.get("pending_action_id")

        if any(w in lower for w in accept_words):
            logger.info(f"Spoken approval ACCEPTED for action {action_id}")
            if self.approval_mgr and action_id:
                self.approval_mgr.approve(action_id)
            self.tts.speak("Action approved. Executing now.")
            self.session.transition_to(VoiceState.LISTENING)
            return "Approved"
        elif any(w in lower for w in reject_words):
            logger.info(f"Spoken approval REJECTED for action {action_id}")
            if self.approval_mgr and action_id:
                self.approval_mgr.reject(action_id)
            self.tts.speak("Action cancelled.")
            self.session.transition_to(VoiceState.LISTENING)
            return "Rejected"
        else:
            prompt = "I did not understand. Please say yes to approve or no to cancel."
            self.tts.speak(prompt)
            return prompt

    def shutdown(self) -> None:
        """Safely shuts down pipeline resources."""
        logger.info("Shutting down VoicePipeline...")
        self._running = False
        self.playback.stop()
        self.stt.shutdown()
        self.tts.shutdown()
        if self.wakeword:
            self.wakeword.shutdown()
        if self.session:
            self.session.transition_to(VoiceState.STOPPED)
        logger.info("VoicePipeline shutdown complete.")
