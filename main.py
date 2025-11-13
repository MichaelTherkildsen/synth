from Modules.Libs.libs import *
import tkinter as tk
import math

class SynthApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SynthPythor")
        self.root.geometry("1200x850")
        
        self._init_variables()
        self._setup_gui()

    def _init_variables(self):
        # Voice 1 Variables (Osc 1 / Filter 1 / Env 1)
        self.osc1_waveform = ctk.StringVar(value="Sawtooth")
        self.osc1_detune = ctk.DoubleVar(value=0)  # cents
        self.osc1_unison = ctk.IntVar(value=1)  # number of unison voices (1-7)
        self.osc1_filter_attack = ctk.DoubleVar(value=0)
        self.osc1_filter_decay = ctk.DoubleVar(value=0.25)
        self.osc1_filter_sustain = ctk.DoubleVar(value=0)
        self.osc1_filter_release = ctk.DoubleVar(value=0.13)
        self.osc1_filter_type = ctk.StringVar(value="Low-pass")
        self.osc1_cutoff = ctk.DoubleVar(value=2000)
        self.osc1_resonance = ctk.DoubleVar(value=1.0) 

        # Voice 2 Variables (Osc 2 / Filter 2 / Env 2)
        self.osc2_enabled = ctk.BooleanVar(value=False)
        self.osc2_waveform = ctk.StringVar(value="Sawtooth")
        self.osc2_detune = ctk.DoubleVar(value=0)  # cents
        self.osc2_unison = ctk.IntVar(value=1)  # number of unison voices (1-7)
        self.osc2_filter_attack = ctk.DoubleVar(value=0)
        self.osc2_filter_decay = ctk.DoubleVar(value=0.1)
        self.osc2_filter_sustain = ctk.DoubleVar(value=0)
        self.osc2_filter_release = ctk.DoubleVar(value=0.1)
        self.osc2_filter_type = ctk.StringVar(value="Low-pass")
        self.osc2_cutoff = ctk.DoubleVar(value=2000)
        self.osc2_resonance = ctk.DoubleVar(value=1.0) 
        self.osc2_mix = ctk.DoubleVar(value=50) # 0 to 100

        # Amp Env Vairables
        self.amp_attack = ctk.DoubleVar(value=0)
        self.amp_decay = ctk.DoubleVar(value=0.1)
        self.amp_sustain = ctk.DoubleVar(value=0)
        self.amp_release = ctk.DoubleVar(value=0.1)

    def play_note(self, note):
        """Triggers note playback in a separate thread."""
        
        # Capture current state from GUI variables
        state = {
            'note': note,
            'duration': 0.5,
            'freq': note_to_frequency(note),
            
            'voice1_params': {
                'waveform': self.osc1_waveform.get(),
                'detune': self.osc1_detune.get(),
                'unison': self.osc1_unison.get(),
                'adsr_vars': {
                    'attack': self.osc1_filter_attack.get(), 'decay': self.osc1_filter_decay.get(),
                    'sustain': self.osc1_filter_sustain.get(), 'release': self.osc1_filter_release.get()
                },
                'filter_vars': {
                    'filter_type': self.osc1_filter_type.get(),
                    'cutoff': self.osc1_cutoff.get(), 'resonance': self.osc1_resonance.get()
                }
            },
            
            'use_voice2': self.osc2_enabled.get(),
            'voice2_params': {
                'waveform': self.osc2_waveform.get(),
                'detune': self.osc2_detune.get(),
                'unison': self.osc2_unison.get(),
                'adsr_vars': {
                    'attack': self.osc2_filter_attack.get(), 'decay': self.osc2_filter_decay.get(),
                    'sustain': self.osc2_filter_sustain.get(), 'release': self.osc2_filter_release.get()
                },
                'filter_vars': {
                    'filter_type': self.osc2_filter_type.get(),
                    'cutoff': self.osc2_cutoff.get(), 'resonance': self.osc2_resonance.get()
                }
            },
            # Amp ADSR (separate from filter ADSR)
            'amp_adsr_vars': {
                'attack': self.amp_attack.get(), 'decay': self.amp_decay.get(),
                'sustain': self.amp_sustain.get(), 'release': self.amp_release.get()
            },
            'mix_level': self.osc2_mix.get() / 100.0
        }
        
        threading.Thread(target=self._play_in_thread, args=(state,)).start()


    def _play_in_thread(self, state):
        """The core audio generation and mixing thread function."""
        def generate_voice_with_unison(osc_params, filter_params, filter_adsr_vars, amp_adsr_vars, base_freq, duration):
            """Generate a voice with optional unison (multiple slightly detuned oscillators)."""
            unison_count = osc_params.get('unison', 1)
            waveform = osc_params['waveform']
            detune = osc_params['detune']
            
            # Generate unison voices
            unison_waves = []
            for i in range(unison_count):
                # Spread unison voices in detune cents
                # Voice 0 is at detune
                # Other voices spread around base detune
                if unison_count == 1:
                    voice_detune = detune
                else:
                    spread = 30  # cents spread around center
                    voice_detune = detune + (i - (unison_count - 1) / 2.0) * (spread / (unison_count - 1))
                
                detune_ratio = 2 ** (voice_detune / 1200.0)
                freq = base_freq * detune_ratio
                
                osc = Oscillator(waveform)
                raw_wave = osc.generate(freq, duration)
                unison_waves.append(raw_wave)
            
            # Mix unison voices (average)
            mixed_wave = np.mean(unison_waves, axis=0)
            
            # Apply filter
            filter_obj = Filter(**filter_params)
            filter_env_adsr = ADSR(**filter_adsr_vars)
            filter_env = filter_env_adsr.get_envelope(duration, total_samples=len(mixed_wave))
            cutoff_knob = clamp(filter_obj.cutoff, 20, MAX_FREQ)
            min_cut = 20.0
            cutoff_env = min_cut + filter_env * (cutoff_knob - min_cut)
            filtered = filter_obj.apply(mixed_wave, cutoff_envelope=cutoff_env)
            
            # Apply amplitude ADSR
            amp_adsr = ADSR(**amp_adsr_vars)
            final = amp_adsr.apply_envelope(filtered, duration)
            
            return final

        # 1. Generate Voice 1 with unison
        wave1 = generate_voice_with_unison(
            state['voice1_params'],
            state['voice1_params']['filter_vars'],
            state['voice1_params']['adsr_vars'],
            state['amp_adsr_vars'],
            state['freq'],
            state['duration']
        )

        # 2. Process Voice 2 and Mix
        final_wave = wave1
        if state['use_voice2']:
            wave2 = generate_voice_with_unison(
                state['voice2_params'],
                state['voice2_params']['filter_vars'],
                state['voice2_params']['adsr_vars'],
                state['amp_adsr_vars'],
                state['freq'],
                state['duration']
            )

            # Ensure same length for mixing
            min_len = min(len(wave1), len(wave2))
            wave1 = wave1[:min_len]
            wave2 = wave2[:min_len]

            mix_level = state['mix_level']
            final_wave = (1.0 - mix_level) * wave1 + mix_level * wave2

        # 3. Final normalization and playback
        final_wave = normalize_wave(final_wave)
        play_wave_dynamic(final_wave, state['duration'])


    # --- GUI Helper Methods (Copied from previous implementation) ---

    def _create_vertical_slider(self, parent_frame, row, col, label_text, variable, from_val, to_val):
        slider = ctk.CTkSlider(
            parent_frame, height=110, orientation="vertical", from_=from_val, to=to_val, variable=variable
        )
        slider.grid(row=row, column=col, padx=5, pady=5)
        ctk.CTkLabel(parent_frame, text=label_text).grid(row=row + 1, column=col, padx=5, pady=5)

    def _create_knob(self, parent_frame, row, col, label_text, variable, min_val, max_val, size=50):
        """Creates a circular knob (tk.Canvas) that controls a DoubleVar between min_val and max_val."""
        frame = ctk.CTkFrame(parent_frame, fg_color=parent_frame.cget('fg_color'))
        frame.grid(row=row, column=col, padx=8, pady=8, sticky="ew")

        ctk.CTkLabel(frame, text=label_text).pack()

        # try to match the CTk frame background; fall back to a dark color
        bg_color = '#2b2b2b'
        try:
            bg_color = parent_frame.cget('fg_color')
        except Exception:
            try:
                bg_color = getattr(frame, '_fg_color', bg_color)
            except Exception:
                pass

        canvas = tk.Canvas(frame, width=size, height=size, highlightthickness=0, bg=bg_color[1], bd=0, relief='raised')
        canvas.pack()

        cx = size / 2
        cy = size / 2
        radius = size * 0.36

        # Draw knob circle (face slightly lighter than the background so it remains visible)
        knob_face = '#333333'
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=knob_face, outline="#444444")

        # Indicator line (will be updated)
        line_len = radius * 0.8
        # initial position for 0.0
        angle = 0
        x2 = cx + line_len * math.cos(angle)
        y2 = cy - line_len * math.sin(angle)
        indicator = canvas.create_line(cx, cy, x2, y2, width=3, fill="#00aaff")

        # Value label
        #val_label = ctk.CTkLabel(frame, text=str(variable.get()))
        #val_label.pack(pady=(2, 0))

        def value_to_angle(val):
            # map value in [min_val, max_val] to an angle on a 270deg arc
            # starting at bottom-left (225deg) and moving clockwise to cover 270deg.
            # clockwise rotation increases the value.
            frac = (val - min_val) / (max_val - min_val) if max_val > min_val else 0
            start_deg = 225.0
            arc = 270.0
            deg = (start_deg - frac * arc) % 360.0
            return math.radians(deg)

        def angle_to_value(rad):
            # Convert angle (radians) to degrees in [0,360)
            deg = math.degrees(rad) % 360.0
            start_deg = 225.0
            arc = 270.0
            diff = (start_deg - deg) % 360.0
            if diff > arc:
                diff = arc
            frac = diff / arc
            return min_val + frac * (max_val - min_val)

        def update_visual_from_value(val):
            ang = value_to_angle(val)
            x2 = cx + line_len * math.cos(ang)
            y2 = cy - line_len * math.sin(ang)
            canvas.coords(indicator, cx, cy, x2, y2)
            # update numeric label
            # format: integer for cutoff, 2 decimals for Q
            #if max_val > 100:
            #    val_label.configure(text=str(int(val)))
            #else:
            #    val_label.configure(text=f"{val:.2f}")

        def on_motion(event):
            # compute angle from center
            dx = event.x - cx
            dy = cy - event.y
            ang = math.atan2(dy, dx)
            new_val = angle_to_value(ang)
            # clamp
            new_val = max(min_val, min(max_val, new_val))
            try:
                variable.set(new_val)
            except Exception:
                pass

        def on_button_press(event):
            on_motion(event)

        # bind mouse events
        canvas.bind("<B1-Motion>", on_motion)
        canvas.bind("<Button-1>", on_button_press)

        # trace variable changes to update visual
        try:
            variable.trace_add('write', lambda *args: update_visual_from_value(variable.get()))
        except Exception:
            # older tkinter
            variable.trace('w', lambda *args: update_visual_from_value(variable.get()))

        # initialize visual
        update_visual_from_value(variable.get())

        return frame

    def _create_adsr_sliders(self, parent_frame, attack_var, decay_var, sustain_var, release_var):
        adsr_vars = [
            (attack_var, "Att"), (decay_var, "Dec"), 
            (sustain_var, "Sus"), (release_var, "Rel")
        ]
        for i, (var, text) in enumerate(adsr_vars):
            ctk.CTkSlider(
                parent_frame, height=110, orientation="vertical", from_=0.0, to=1.0, variable=var
            ).grid(row=1, column=i, padx=5, pady=5)
            ctk.CTkLabel(parent_frame, text=text).grid(row=2, column=i, padx=5, pady=5)
            
    def _create_oscillator_frame(self, parent_frame, row, col, label, waveform_var, detune_var, unison_var, enabled_var=None, mix_var=None):
        frame = ctk.CTkFrame(parent_frame)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        
        # Title (spans all columns)
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        # Waveform menu (spans all columns)
        ctk.CTkOptionMenu(frame, width=170, values=["Sine", "Square", "Square*4", "Square*8", "Square*16", "Sawtooth", "Sawtooth*4", "Sawtooth*8", "Sawtooth*16"], variable=waveform_var).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        if enabled_var:
            # Enable checkbox (spans all columns)
            ctk.CTkCheckBox(frame, text="Enable Voice", variable=enabled_var).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            
            # Mix slider (spans all columns)
            ctk.CTkLabel(frame, text="Mix (%)").grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            ctk.CTkSlider(frame, orientation="horizontal", from_=0, to=100, variable=mix_var).grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            
            # Detune knob (left) - row 5
            self._create_knob(frame, 5, 0, "Detune (¢)", detune_var, -100, 100, size=50)
            
            # Unison knob (right) - row 5
            self._create_knob(frame, 5, 1, "Unison", unison_var, 1, 7, size=50)
        else:
            # Detune knob (left) - row 2
            self._create_knob(frame, 2, 0, "Detune (¢)", detune_var, -100, 100, size=50)
            
            # Unison knob (right) - row 2
            self._create_knob(frame, 2, 1, "Unison", unison_var, 1, 7, size=50)

    def _create_filter_frame(self, parent_frame, row, col, label, type_var, cutoff_var, resonance_var):
        frame = ctk.CTkFrame(parent_frame)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="n")
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=10, pady=5)
        ctk.CTkOptionMenu(frame, values=["None", "Low-pass", "High-pass", "Band-pass"], variable=type_var
        ).grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        # Replace vertical sliders with turnable knobs
        self._create_knob(frame, 2, 0, "Freq (Hz)", cutoff_var, 20, 20000)
        self._create_knob(frame, 2, 1, "Res (Q)", resonance_var, 1, 10)
        ctk.CTkLabel(frame, text="").grid(row=3, column=2, rowspan=2, padx=5)

    def _create_adsr_frame(self, parent_frame, row, col, label, attack_var, decay_var, sustain_var, release_var):
        frame = ctk.CTkFrame(parent_frame)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="n")
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, padx=10, pady=5)
        self._create_adsr_sliders(frame, attack_var, decay_var, sustain_var, release_var)

    def _create_piano_keys(self, piano_frame):
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
        for i, (key, midi_note) in enumerate(white_keys):
            button = ctk.CTkButton(
                piano_frame, text="", command=partial(self.play_note, midi_note),
                width=50, height=150, fg_color="white", text_color="black", corner_radius=0
            )
            button.grid(row=0, column=i, padx=0, pady=0, sticky="n")
        for i, key_data in enumerate(black_keys):
            if key_data is None: continue
            key, midi_note = key_data
            button = ctk.CTkButton(
                piano_frame, text="", command=partial(self.play_note, midi_note),
                width=30, height=100, fg_color="black", text_color="white", corner_radius=0
            )
            button.place(x=(50 * i + 35), y=0) 

    def _setup_gui(self):
        controls_frame = ctk.CTkFrame(self.root)
        controls_frame.pack(pady=10, padx=10, fill="both")

        self._create_oscillator_frame(controls_frame, 0, 0, "Oscillator 1", self.osc1_waveform, self.osc1_detune, self.osc1_unison)
        self._create_filter_frame(controls_frame, 0, 1, "Filter 1", self.osc1_filter_type, self.osc1_cutoff, self.osc1_resonance)
        self._create_adsr_frame(controls_frame, 0, 3, "Filter 1 Env", self.osc1_filter_attack, self.osc1_filter_decay, self.osc1_filter_sustain, self.osc1_filter_release)

        self._create_oscillator_frame(controls_frame, 1, 0, "Oscillator 2", self.osc2_waveform, self.osc2_detune, self.osc2_unison, self.osc2_enabled, self.osc2_mix)
        self._create_filter_frame(controls_frame, 0, 2, "Filter 2", self.osc2_filter_type, self.osc2_cutoff, self.osc2_resonance)
        self._create_adsr_frame(controls_frame, 0, 4, "Filter 2 Env", self.osc2_filter_attack, self.osc2_filter_decay, self.osc2_filter_sustain, self.osc2_filter_release)

        self._create_adsr_frame(controls_frame,0, 5, "Amp Env", self.amp_attack, self.amp_decay, self.amp_sustain, self.amp_release)
        
        # Make controls_frame height dynamic to match content
        controls_frame.update_idletasks()
        controls_frame.configure(height=controls_frame.winfo_reqheight())
        
        piano_frame = ctk.CTkFrame(self.root, height=150)
        piano_frame.pack(side="bottom", fill="x")
        self._create_piano_keys(piano_frame)

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    app = SynthApp(root)
    
    root.mainloop()