from Modules.Libs.libs import *

class Voice:
    """Represents a single sound generation module (Oscillator + ADSR + Filter)."""
    
    def __init__(self, waveform, adsr_vars, filter_vars):
        self.oscillator = Oscillator(waveform)
        self.adsr = ADSR(**adsr_vars)
        self.filter = Filter(**filter_vars)

    def generate_and_process(self, frequency, duration):
        """Generates the raw wave, applies ADSR, and applies the filter."""
        # 1. Generate Raw Wave
        raw_wave = self.oscillator.generate(frequency, duration)
        
        # 2. Apply ADSR Envelope
        enveloped_wave = self.adsr.apply_envelope(raw_wave, duration)
        
        # 3. Apply Filter
        filtered_wave = self.filter.apply(enveloped_wave)
        
        return filtered_wave