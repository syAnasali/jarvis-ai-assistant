"""Diagnostic script testing VoiceActivityDetector speech/silence boundary tracking."""

import sys
sys.path.insert(0, ".")

from datetime import datetime, timezone
import numpy as np
from app.voice.models import AudioFrame
from app.voice.vad import EnergyBasedVAD


def main() -> None:
    print("==================================================")
    print("Testing VoiceActivityDetector (VAD) Diagnostics")
    print("==================================================")

    vad = EnergyBasedVAD(threshold=100.0, end_silence_duration=0.2)
    assert vad.get_state() == "WAITING_FOR_SPEECH"

    # Silent frame
    silent_pcm = np.zeros(160, dtype=np.int16).tobytes()
    frame1 = AudioFrame(
        pcm_data=silent_pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )
    vad.process_frame(frame1)
    assert vad.get_state() == "WAITING_FOR_SPEECH"

    # Loud speech frame
    loud_pcm = (np.ones(160, dtype=np.int16) * 5000).tobytes()
    frame2 = AudioFrame(
        pcm_data=loud_pcm,
        sample_rate=16000,
        channels=1,
        sample_width=2,
        timestamp=datetime.now(timezone.utc)
    )
    vad.process_frame(frame2)
    assert vad.get_state() == "SPEECH_ACTIVE"
    print("PASS: VAD speech start boundary transition to SPEECH_ACTIVE verified.")

    print("\nALL VAD DIAGNOSTICS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
