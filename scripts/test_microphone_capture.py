"""Diagnostic script for enumerating and testing the physical microphone capture."""

import sys
import time
from app.voice.capture import SoundDeviceAudioCapture
from app.voice.vad import EnergyBasedVAD

def main() -> None:
    print("=== Physical Microphone Capture Diagnostic ===")
    
    capture = SoundDeviceAudioCapture()
    devices = capture.list_input_devices()
    
    if not devices:
        print("[FAIL] No input devices found. Verify microphone connections.")
        sys.exit(1)
        
    print("\nAvailable Input Devices:")
    default_dev = None
    for dev in devices:
        star = " (DEFAULT)" if dev["is_default"] else ""
        print(f" - ID {dev['device_id']}: '{dev['name']}' (channels: {dev['max_input_channels']}){star}")
        if dev["is_default"]:
            default_dev = dev

    # Resolve default device
    if default_dev:
        print(f"\nSelected default device: '{default_dev['name']}' (ID: {default_dev['device_id']})")
    else:
        default_dev = devices[0]
        print(f"\nNo default flag. Selected first device: '{default_dev['name']}' (ID: {default_dev['device_id']})")

    # Set up VAD
    vad = EnergyBasedVAD(threshold=300.0, wait_timeout=5.0, min_speech_duration=0.25, end_silence_duration=0.8)
    
    print("\n[VAD configuration]")
    print(" - Wait-for-speech timeout: 5.0 seconds")
    print(" - Energy threshold: 300.0")
    print(" - End-of-speech silence: 0.8 seconds")
    
    print("\nReady to record. Please speak a single word or sentence when prompted.")
    input("Press Enter to start recording... ")
    
    try:
        capture.open_capture(device_id=default_dev["device_id"])
        print("[Recording started... Speak now!]")
        
        while True:
            frame = capture.read_frame()
            vad.process_frame(frame)
            state = vad.get_state()
            
            if state == "SPEECH_ACTIVE":
                print(".", end="", flush=True)
            elif state in ("COMPLETE", "TIMEOUT", "ERROR"):
                print()
                break
                
        capture.close_capture()
        
        final_state = vad.get_state()
        print(f"\nRecording stopped. Final VAD State: {final_state}")
        
        if final_state == "TIMEOUT":
            print("[TIMEOUT] Listening timed out. No speech detected.")
        elif final_state == "COMPLETE":
            segment = vad.get_captured_segment()
            if segment:
                print(f"[PASS] Speech successfully captured!")
                print(f" - Audio Duration: {segment.duration_seconds:.2f} seconds")
                print(f" - Bytes count:   {len(segment.pcm_data)} bytes")
            else:
                print("[FAIL] State complete but segment was None.")
        else:
            print(f"[FAIL] VAD ended in state: {final_state}")
            
    except Exception as e:
        print(f"\n[FAIL] Exception during microphone test: {e}")
        capture.close_capture()
        sys.exit(1)

if __name__ == "__main__":
    main()
