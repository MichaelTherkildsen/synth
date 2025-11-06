import customtkinter as ctk
from functools import partial
from scipy.signal import butter, lfilter
import numpy as np
import sounddevice as sd
import threading

# Low-pass filter
def low_pass_filter(data, cutoff, samplerate, resonance=1):
    nyquist = 0.5 * samplerate
    normal_cutoff = cutoff / nyquist
    b, a = butter(resonance, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

# High-pass filter
def high_pass_filter(data, cutoff, samplerate, resonance=1):
    nyquist = 0.5 * samplerate
    normal_cutoff = cutoff / nyquist
    b, a = butter(resonance, normal_cutoff, btype='high', analog=False)
    return lfilter(b, a, data)

# Band-pass filter
def band_pass_filter(data, low_cutoff, high_cutoff, samplerate, resonance=1):
    nyquist = 0.5 * samplerate
    low = low_cutoff / nyquist
    high = high_cutoff / nyquist
    b, a = butter(resonance, [low, high], btype='band', analog=False)
    return lfilter(b, a, data)

# Precompute waveforms for all MIDI notes
precomputed_waves = {}

def precompute_waveforms():
    for note in range(21, 109):  # MIDI range A0 (21) to C8 (108)
        frequency = note_to_frequency(note)
        duration = 0.5  # Fixed duration for precomputing
        waveforms = {}  # A dictionary to hold waveforms for this note
        # Precompute waveforms for each oscillator and ADSR setting
        for waveform in ["Sine", "Square", "Sawtooth"]:
            wave = generate_wave(waveform, frequency, duration)
            # Apply ADSR envelope for oscillator 1 settings
            wave = apply_adsr_envelope(
                wave,
                osc1_attack.get(),
                osc1_decay.get(),
                osc1_sustain.get(),
                osc1_release.get(),
                duration
            )
            waveforms[waveform] = wave  # Store the waveform for this type
        precomputed_waves[note] = waveforms  # Store waveforms for this note

# Sampling rate (samples per second)
SAMPLE_RATE = 44100

# Waveform generation functions
def generate_sine_wave(frequency, duration, amplitude=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * frequency * t)

def generate_square_wave(frequency, duration, amplitude=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return amplitude * np.sign(np.sin(2 * np.pi * frequency * t))

def generate_sawtooth_wave(frequency, duration, amplitude=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return amplitude * (2 * (t * frequency - np.floor(0.5 + t * frequency)))

# ADSR Envelope generator
def apply_adsr_envelope(wave, attack, decay, sustain, release, duration):
    total_samples = len(wave)
    attack_samples = int(attack * SAMPLE_RATE)
    decay_samples = int(decay * SAMPLE_RATE)
    sustain_samples = int((duration - attack - decay - release) * SAMPLE_RATE)
    release_samples = int(release * SAMPLE_RATE)

    # Generate envelope
    envelope = np.zeros(total_samples)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if decay_samples > 0:
        envelope[attack_samples:attack_samples + decay_samples] = np.linspace(1, sustain, decay_samples)
    if sustain_samples > 0:
        envelope[attack_samples + decay_samples:attack_samples + decay_samples + sustain_samples] = sustain
    if release_samples > 0:
        envelope[-release_samples:] = np.linspace(sustain, 0, release_samples)

    # Apply envelope to wave
    return wave * envelope

# Play generated wave with dynamic ADSR settings
def play_wave_dynamic(wave, attack, decay, sustain, release, duration):
    total_samples = len(wave)
    attack_samples = int(attack * SAMPLE_RATE)
    decay_samples = int(decay * SAMPLE_RATE)
    release_samples = int(release * SAMPLE_RATE)
    sustain_samples = total_samples - (attack_samples + decay_samples + release_samples)

    # Generate ADSR envelope dynamically
    def callback(outdata, frames, time, status):
        if status:
            print(status)  # Handle audio buffer errors (if any)
        
        start_idx = callback.current_idx
        end_idx = start_idx + frames
        if end_idx > total_samples:
            end_idx = total_samples
        
        # Apply ADSR envelope dynamically
        envelope = np.zeros(frames)
        for i in range(frames):
            idx = start_idx + i
            if idx < attack_samples:
                envelope[i] = idx / attack_samples
            elif idx < attack_samples + decay_samples:
                envelope[i] = 1 - ((idx - attack_samples) / decay_samples) * (1 - sustain)
            elif idx < attack_samples + decay_samples + sustain_samples:
                envelope[i] = sustain
            elif idx < total_samples:
                envelope[i] = sustain - ((idx - (attack_samples + decay_samples + sustain_samples)) / release_samples) * sustain
            else:
                envelope[i] = 0
        
        # Apply the envelope to the wave
        outdata[:, 0] = wave[start_idx:end_idx] * envelope
        callback.current_idx = end_idx

        # Stop playback when all samples are played
        if end_idx >= total_samples:
            raise sd.CallbackStop

    callback.current_idx = 0

    # Start the stream
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
        sd.sleep(int(duration * 1000))

# Convert MIDI note to frequency
def note_to_frequency(note):
    # A4 = 440 Hz, note number 69 in MIDI
    A4 = 440.0
    return A4 * 2**((note - 69) / 12.0)

# Generate wave based on selected waveform
def generate_wave(waveform, frequency, duration, amplitude=1.0):
    if waveform == "Sine":
        return generate_sine_wave(frequency, duration, amplitude)
    elif waveform == "Square":
        return generate_square_wave(frequency, duration, amplitude)
    elif waveform == "Sawtooth":
        return generate_sawtooth_wave(frequency, duration, amplitude)
    else:
        return np.zeros(int(SAMPLE_RATE * duration))  # Silence for invalid waveform

# Function to play a note with two oscillators and ADSR envelopes
def play_note(note):
    def play_in_thread(
        note, 
        waveform1, 
        osc1_adsr, 
        osc1_filter_type, 
        osc1_cutoff_freq, 
        osc1_resonance_value,  # NEW
        use_osc2, 
        waveform2, 
        osc2_adsr, 
        osc2_filter_type, 
        osc2_cutoff_freq, 
        osc2_resonance_value,  # NEW
        osc2_mix_value
    ):
        frequency = note_to_frequency(note)
        duration = 0.5  # Fixed duration for simplicity

        # Generate Oscillator 1 waveform
        wave1 = generate_wave(waveform1, frequency, duration)
        wave1 = apply_adsr_envelope(
            wave1,
            osc1_adsr['attack'],
            osc1_adsr['decay'],
            osc1_adsr['sustain'],
            osc1_adsr['release'],
            duration
        )
        # Apply filter to Oscillator 1
        if osc1_filter_type == "Low-pass":
            wave1 = low_pass_filter(wave1, osc1_cutoff_freq, SAMPLE_RATE, osc1_resonance_value)
        elif osc1_filter_type == "High-pass":
            wave1 = high_pass_filter(wave1, osc1_cutoff_freq, SAMPLE_RATE, osc1_resonance_value)
        elif osc1_filter_type == "Band-pass":
            wave1 = band_pass_filter(wave1, osc1_cutoff_freq, osc1_cutoff_freq * 1.5, SAMPLE_RATE, osc1_resonance_value)

        # Generate Oscillator 2 waveform if enabled
        if use_osc2:
            wave2 = generate_wave(waveform2, frequency, duration)
            wave2 = apply_adsr_envelope(
                wave2,
                osc2_adsr['attack'],
                osc2_adsr['decay'],
                osc2_adsr['sustain'],
                osc2_adsr['release'],
                duration
            )
            # Apply filter to Oscillator 2
            if osc2_filter_type == "Low-pass":
                wave2 = low_pass_filter(wave2, osc2_cutoff_freq, SAMPLE_RATE, osc2_resonance_value)
            elif osc2_filter_type == "High-pass":
                wave2 = high_pass_filter(wave2, osc2_cutoff_freq, SAMPLE_RATE, osc2_resonance_value)
            elif osc2_filter_type == "Band-pass":
                wave2 = band_pass_filter(wave2, osc2_cutoff_freq, osc2_cutoff_freq * 1.5, SAMPLE_RATE, osc2_resonance_value)

            # Mix Oscillator 1 and Oscillator 2
            wave = (1 - osc2_mix_value) * wave1 + osc2_mix_value * wave2
        else:
            wave = wave1  # Only Oscillator 1 is active

        # Play the resulting waveform with dynamic ADSR
        play_wave_dynamic(
            wave,
            osc1_adsr['attack'],
            osc1_adsr['decay'],
            osc1_adsr['sustain'],
            osc1_adsr['release'],
            duration
        )

    # Capture the current state of all variables
    waveform1 = osc1_waveform.get()
    osc1_adsr = {
        'attack': osc1_attack.get(),
        'decay': osc1_decay.get(),
        'sustain': osc1_sustain.get(),
        'release': osc1_release.get()
    }
    selected_osc1_filter_type = osc1_filter_type.get()
    osc1_cutoff_freq = osc1_cutoff.get()
    osc1_resonance_value = osc1_resonance.get()

    use_osc2 = osc2_enabled.get()
    waveform2 = osc2_waveform.get()
    osc2_adsr = {
        'attack': osc2_attack.get(),
        'decay': osc2_decay.get(),
        'sustain': osc2_sustain.get(),
        'release': osc2_release.get()
    }
    selected_osc2_filter_type = osc2_filter_type.get()
    osc2_cutoff_freq = osc2_cutoff.get()
    osc2_resonance_value = osc2_resonance.get()
    osc2_mix_value = osc2_mix.get() / 100.0  # Convert to percentage

    # Start playback in a separate thread, passing captured state
    threading.Thread(
        target=play_in_thread,
        args=(
            note, 
            waveform1, 
            osc1_adsr, 
            selected_osc1_filter_type, 
            osc1_cutoff_freq, 
            osc1_resonance_value,
            use_osc2, 
            waveform2, 
            osc2_adsr, 
            selected_osc2_filter_type, 
            osc2_cutoff_freq, 
            osc2_resonance_value, 
            osc2_mix_value
        )
    ).start()

# Initialize customtkinter
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

# Create the main application window
root = ctk.CTk()
root.title("Mike T")
root.geometry("1200x600")

# Main control frame
controls_frame = ctk.CTkFrame(root)
controls_frame.pack(pady=10, fill="x")

# Oscillator 1 Section
osc1_frame = ctk.CTkFrame(controls_frame, height=200, width=200)  # Matching dimensions
osc1_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")

osc1_label = ctk.CTkLabel(osc1_frame, text="Oscillator 1")
osc1_label.pack(pady=5)
osc1_waveform = ctk.StringVar(value="Sine")  # Default waveform
osc1_dropdown = ctk.CTkOptionMenu(osc1_frame, width=200, values=["Sine", "Square", "Sawtooth"], variable=osc1_waveform)
osc1_dropdown.pack(pady=5, padx=15)

# Filter for osc1
filter1_frame = ctk.CTkFrame(controls_frame)
filter1_frame.grid(row=0, column=1, padx=10, pady=10, sticky="w")
ctk.CTkLabel(filter1_frame, text="Filter 1").grid(row=0, padx=10, pady=10)
osc1_filter_frame = ctk.CTkFrame(filter1_frame)
osc1_filter_frame.grid(row=1)

osc1_filter_type = ctk.StringVar(value="None")  # Default filter type
osc1_filter_dropdown = ctk.CTkOptionMenu(
    osc1_filter_frame, 
    values=["None", "Low-pass", "High-pass", "Band-pass"], 
    variable=osc1_filter_type
)
osc1_filter_dropdown.grid(rowspan=2, row=0, column=0, padx=5, pady=5, sticky="n")

osc1_cutoff = ctk.DoubleVar(value=1000)  # Default cutoff frequency
osc1_cutoff_slider = ctk.CTkSlider(
    osc1_filter_frame, 
    height=110,
    orientation="vertical",
    from_=20, 
    to=20000, 
    variable=osc1_cutoff
)
osc1_cutoff_slider.grid(row=0, column=1, padx=5, pady=5)

osc1_cutoff_label = ctk.CTkLabel(osc1_filter_frame, text="Cut")
osc1_cutoff_label.grid(row=1, column=1, padx=5, pady=5)

osc1_resonance = ctk.DoubleVar(value=1)  # Default resonance is 1
osc1_resonance_slider = ctk.CTkSlider(
    osc1_filter_frame,
    height=110,
    orientation="vertical",
    from_=1,  # Minimum resonance (1 is the default)
    to=10,    # Maximum resonance (adjust as needed)
    variable=osc1_resonance
)
osc1_resonance_slider.grid(row=0, column=2, padx=5, pady=5)

osc1_resonance_label = ctk.CTkLabel(osc1_filter_frame, text="Res")
osc1_resonance_label.grid(row=1, column=2, padx=5, pady=5)

# ADSR sliders for Oscillator 1
env1_frame = ctk.CTkFrame(controls_frame)
env1_frame.grid(row=0, column=3, padx=10, pady=10, sticky="w")
ctk.CTkLabel(env1_frame, text="Envelope 1").grid(row=0, padx=10, pady=10)
osc1_adsr_frame = ctk.CTkFrame(env1_frame)
osc1_adsr_frame.grid(row=1)

osc1_attack = ctk.DoubleVar(value=0.1)
osc1_decay = ctk.DoubleVar(value=0.1)
osc1_sustain = ctk.DoubleVar(value=0.8)
osc1_release = ctk.DoubleVar(value=0.3)

ctk.CTkSlider(osc1_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc1_attack).grid(row=0, column=0, padx=5, pady=5)
ctk.CTkSlider(osc1_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc1_decay).grid(row=0, column=1, padx=5, pady=5)
ctk.CTkSlider(osc1_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc1_sustain).grid(row=0, column=2, padx=5, pady=5)
ctk.CTkSlider(osc1_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc1_release).grid(row=0, column=3, padx=5, pady=5)

ctk.CTkLabel(osc1_adsr_frame, text="Att").grid(row=1, column=0, padx=5, pady=5)
ctk.CTkLabel(osc1_adsr_frame, text="Dec").grid(row=1, column=1, padx=5, pady=5)
ctk.CTkLabel(osc1_adsr_frame, text="Sus").grid(row=1, column=2, padx=5, pady=5)
ctk.CTkLabel(osc1_adsr_frame, text="Rel").grid(row=1, column=3, padx=5, pady=5)

# Spacer to balance the frame
osc1_spacer = ctk.CTkLabel(osc1_frame, text="")  # Empty label as a spacer
osc1_spacer.pack(pady=50)  # Add padding to match Oscillator 2 height

# Oscillator 2 Section
osc2_frame = ctk.CTkFrame(controls_frame, height=200, width=200)  # Matching dimensions
osc2_frame.grid(row=1, column=0, padx=10, pady=10, sticky="w")

osc2_label = ctk.CTkLabel(osc2_frame, text="Oscillator 2")
osc2_label.pack(pady=5, padx=10)
osc2_waveform = ctk.StringVar(value="Sine")  # Default waveform
osc2_dropdown = ctk.CTkOptionMenu(osc2_frame, width=200, values=["Sine", "Square", "Sawtooth"], variable=osc2_waveform)
osc2_dropdown.pack(pady=5, padx=15)

osc2_enabled = ctk.BooleanVar(value=False)
osc2_checkbox = ctk.CTkCheckBox(osc2_frame, text="Enable Oscillator 2", variable=osc2_enabled)
osc2_checkbox.pack(pady=5)

# Oscillator 2 mix slider
osc2_mix_label = ctk.CTkLabel(osc2_frame, text="Oscillator 2 Mix:")
osc2_mix_label.pack(pady=5, padx=10)
osc2_mix = ctk.DoubleVar(value=50)  # Default mix is 50%
osc2_mix_slider = ctk.CTkSlider(osc2_frame, orientation="horizontal", from_=0, to=100, variable=osc2_mix)
osc2_mix_slider.pack(pady=5)

# Filter for osc2
filter2_frame = ctk.CTkFrame(controls_frame)
filter2_frame.grid(row=0, column=2, padx=10, pady=10, sticky="w")
ctk.CTkLabel(filter2_frame, text="Filter 2").grid(row=0, padx=10, pady=10)
osc2_filter_frame = ctk.CTkFrame(filter2_frame)
osc2_filter_frame.grid(row=1)

osc2_filter_type = ctk.StringVar(value="None")  # Default filter type
osc2_filter_dropdown = ctk.CTkOptionMenu(
    osc2_filter_frame, 
    values=["None", "Low-pass", "High-pass", "Band-pass"], 
    variable=osc2_filter_type
)
osc2_filter_dropdown.grid(rowspan=2, row=0, column=0, padx=5, pady=5, sticky="n")

osc2_cutoff = ctk.DoubleVar(value=1000)  # Default cutoff frequency
osc2_cutoff_slider = ctk.CTkSlider(
    osc2_filter_frame, 
    height=110,
    orientation="vertical",
    from_=20, 
    to=20000, 
    variable=osc2_cutoff
)
osc2_cutoff_slider.grid(row=0, column=1, padx=5, pady=5)

osc2_cutoff_label = ctk.CTkLabel(osc2_filter_frame, text="Cut")
osc2_cutoff_label.grid(row=1, column=1, padx=5, pady=5)

osc2_resonance = ctk.DoubleVar(value=1)  # Default resonance is 1
osc2_resonance_slider = ctk.CTkSlider(
    osc2_filter_frame,
    height=110,
    orientation="vertical",
    from_=1,  # Minimum resonance (1 is the default)
    to=10,    # Maximum resonance (adjust as needed)
    variable=osc2_resonance
)
osc2_resonance_slider.grid(row=0, column=2, padx=5, pady=5)

osc2_resonance_label = ctk.CTkLabel(osc2_filter_frame, text="Res")
osc2_resonance_label.grid(row=1, column=2, padx=5, pady=5)

# ADSR sliders for Oscillator 2
env2_frame = ctk.CTkFrame(controls_frame)
env2_frame.grid(row=0, column=4, padx=10, pady=10, sticky="w")
ctk.CTkLabel(env2_frame, text="Envelope 2").grid(row=0, padx=10, pady=10)
osc2_adsr_frame = ctk.CTkFrame(env2_frame)
osc2_adsr_frame.grid(row=1)

osc2_attack = ctk.DoubleVar(value=0.1)
osc2_decay = ctk.DoubleVar(value=0.1)
osc2_sustain = ctk.DoubleVar(value=0.8)
osc2_release = ctk.DoubleVar(value=0.3)

ctk.CTkSlider(osc2_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc2_attack).grid(row=0, column=0, padx=5, pady=5)
ctk.CTkSlider(osc2_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc2_decay).grid(row=0, column=1, padx=5, pady=5)
ctk.CTkSlider(osc2_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc2_sustain).grid(row=0, column=2, padx=5, pady=5)
ctk.CTkSlider(osc2_adsr_frame, height=110, orientation="vertical", from_=0, to=1, variable=osc2_release).grid(row=0, column=3, padx=5, pady=5)

ctk.CTkLabel(osc2_adsr_frame, text="Att").grid(row=1, column=0, padx=5, pady=5)
ctk.CTkLabel(osc2_adsr_frame, text="Dec").grid(row=1, column=1, padx=5, pady=5)
ctk.CTkLabel(osc2_adsr_frame, text="Sus").grid(row=1, column=2, padx=5, pady=5)
ctk.CTkLabel(osc2_adsr_frame, text="Rel").grid(row=1, column=3, padx=5, pady=5)

# Piano Frame
piano_frame = ctk.CTkFrame(root, width=1200, height=150)
piano_frame.pack(side="bottom", fill="x")

# Define piano keys
white_keys = [
    ("C", 48), ("D", 50), ("E", 52), ("F", 53), ("G", 55), ("A", 57), ("B", 59),
    ("C", 60), ("D", 62), ("E", 64), ("F", 65), ("G", 67), ("A", 69), ("B", 71),
    ("C", 72), ("D", 74), ("E", 76), ("F", 77), ("G", 79), ("A", 81), ("B", 83),
    ("C", 84), ("D", 86), ("E", 88), ("F", 89), ("G", 91), ("A", 93), ("B", 95)
]
black_keys = [
    ("C#", 49), ("D#", 51), None, ("F#", 54), ("G#", 56), ("A#", 58), None,
    ("C#", 61), ("D#", 63), None, ("F#", 66), ("G#", 68), ("A#", 70), None,
    ("C#", 73), ("D#", 75), None, ("F#", 78), ("G#", 80), ("A#", 82), None,
    ("C#", 85), ("D#", 87), None, ("F#", 90), ("G#", 92), ("A#", 94), None
]

# Add white keys
for i, (key, midi_note) in enumerate(white_keys):
    button = ctk.CTkButton(
        piano_frame,
        text=key,
        command=partial(play_note, midi_note),
        width=50,
        height=150,
        fg_color="white",
        text_color="black",
        corner_radius=0
    )
    button.grid(row=0, column=i, padx=0, pady=0, sticky="n")

# Add black keys
for i, key_data in enumerate(black_keys):
    if key_data is None:
        continue  # Skip spaces where there are no black keys
    key, midi_note = key_data
    button = ctk.CTkButton(
        piano_frame,
        text=key,
        command=partial(play_note, midi_note),
        width=30,
        height=100,
        fg_color="black",
        text_color="white",
        corner_radius=0
    )
    # Position black keys slightly offset above white keys
    button.place(x=(50 * i + 35), y=0)  # Offset black keys horizontally and vertically

# Run the application
precompute_waveforms()
root.mainloop()