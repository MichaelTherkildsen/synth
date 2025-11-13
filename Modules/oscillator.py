from Modules.Libs.libs import *

class Oscillator:
    """Generates base waveforms (Sine, Square, or Sawtooth)."""
    
    def __init__(self, waveform):
        self.waveform = waveform
    
    def generate(self, frequency, duration, amplitude=1.0):
        """Generates the base waveform."""
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        
        if self.waveform == "Sine":
            return amplitude * np.sin(2 * np.pi * frequency * t)
        elif self.waveform == "Square":
            return amplitude * np.sign(np.sin(2 * np.pi * frequency * t))
        elif self.waveform == "Sawtooth":
            return amplitude * (2 * (t * frequency - np.floor(0.5 + t * frequency)))
        elif self.waveform == "Square*4":
            base = np.sign(np.sin(2 * np.pi * frequency * t))
            # Add harmonics: 3rd, 5th, 7th, 9th with decreasing amplitude
            harmonics = (1/3) * np.sign(np.sin(2 * np.pi * 3 * frequency * t))
            harmonics += (1/5) * np.sign(np.sin(2 * np.pi * 5 * frequency * t))
            harmonics += (1/7) * np.sign(np.sin(2 * np.pi * 7 * frequency * t))
            harmonics += (1/9) * np.sign(np.sin(2 * np.pi * 9 * frequency * t))
            return amplitude * (base + harmonics) / 4.0
        elif self.waveform == "Square*8":
            base = np.sign(np.sin(2 * np.pi * frequency * t))
            harmonics = (1/3) * np.sign(np.sin(2 * np.pi * 3 * frequency * t))
            harmonics += (1/5) * np.sign(np.sin(2 * np.pi * 5 * frequency * t))
            harmonics += (1/7) * np.sign(np.sin(2 * np.pi * 7 * frequency * t))
            harmonics += (1/9) * np.sign(np.sin(2 * np.pi * 9 * frequency * t))
            harmonics += (1/11) * np.sign(np.sin(2 * np.pi * 11 * frequency * t))
            harmonics += (1/13) * np.sign(np.sin(2 * np.pi * 13 * frequency * t))
            harmonics += (1/15) * np.sign(np.sin(2 * np.pi * 15 * frequency * t))
            return amplitude * (base + harmonics) / 8.0
        elif self.waveform == "Square*16":
            base = np.sign(np.sin(2 * np.pi * frequency * t))
            harmonics = 0
            for n in range(3, 32, 2):  # odd harmonics 3,5,7,...,31
                harmonics += (1/n) * np.sign(np.sin(2 * np.pi * n * frequency * t))
            return amplitude * (base + harmonics) / 16.0
        elif self.waveform == "Sawtooth*4":
            base = 2 * (t * frequency - np.floor(0.5 + t * frequency))
            harmonics = (1/2) * (2 * (t * 2 * frequency - np.floor(0.5 + t * 2 * frequency)))
            harmonics += (1/3) * (2 * (t * 3 * frequency - np.floor(0.5 + t * 3 * frequency)))
            harmonics += (1/4) * (2 * (t * 4 * frequency - np.floor(0.5 + t * 4 * frequency)))
            return amplitude * (base + harmonics) / 4.0
        elif self.waveform == "Sawtooth*8":
            base = 2 * (t * frequency - np.floor(0.5 + t * frequency))
            harmonics = 0
            for n in range(2, 9):
                harmonics += (1/n) * (2 * (t * n * frequency - np.floor(0.5 + t * n * frequency)))
            return amplitude * (base + harmonics) / 8.0
        elif self.waveform == "Sawtooth*16":
            base = 2 * (t * frequency - np.floor(0.5 + t * frequency))
            harmonics = 0
            for n in range(2, 17):
                harmonics += (1/n) * (2 * (t * n * frequency - np.floor(0.5 + t * n * frequency)))
            return amplitude * (base + harmonics) / 16.0
        else:
            return np.zeros(len(t))
