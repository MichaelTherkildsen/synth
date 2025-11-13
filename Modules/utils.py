from Modules.Libs.libs import *

# Global Constants
SAMPLE_RATE = 44100
MAX_FREQ = SAMPLE_RATE / 2 - 1 # Nyquist frequency limit

def note_to_frequency(note):
    """Converts a MIDI note number to its corresponding frequency in Hz."""
    # A4 = 440 Hz, note number 69 in MIDI
    A4 = 440.0
    return A4 * 2**((note - 69) / 12.0)

def normalize_wave(wave):
    """Normalizes the wave amplitude to prevent clipping."""
    max_amp = np.max(np.abs(wave))
    return wave / max_amp if max_amp > 0 else wave

def clamp(value, min_value, max_value):
    """Clamps a value within a specified range."""
    return max(min_value, min(value, max_value))

def play_wave_dynamic(wave, duration):
    """Plays a wave using a sounddevice stream."""
    total_samples = len(wave)
    
    def callback(outdata, frames, time, status):
        if status: pass
        
        start_idx = callback.current_idx
        end_idx = start_idx + frames
        actual_end_idx = min(end_idx, total_samples)
        num_samples_to_write = actual_end_idx - start_idx

        if num_samples_to_write < frames:
            outdata[:num_samples_to_write, 0] = wave[start_idx:actual_end_idx]
            outdata[num_samples_to_write:, 0] = 0.0
        else:
            outdata[:, 0] = wave[start_idx:actual_end_idx]
        
        callback.current_idx = actual_end_idx

        if actual_end_idx >= total_samples:
            raise sd.CallbackStop

    callback.current_idx = 0

    try:
        with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
            sd.sleep(int(duration * 1000) + 100)
    except Exception:
        pass # Handle audio stream error silently