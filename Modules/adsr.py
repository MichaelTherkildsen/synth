from Modules.Libs.libs import *

class ADSR:
    """Manages Attack, Decay, Sustain, and Release envelope generation."""
    def __init__(self, attack, decay, sustain, release):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
    
    def apply_envelope(self, wave, duration):
        """Applies the ADSR envelope to a full waveform."""
        total_samples = len(wave)
        envelope = self.get_envelope(duration, total_samples=total_samples)
        return wave * envelope

    def get_envelope(self, duration, total_samples=None):
        """Return the ADSR envelope as a numpy array of length total_samples.

        If total_samples is None, it's calculated from duration and SAMPLE_RATE.
        """
        if total_samples is None:
            total_samples = int(max(0, duration * SAMPLE_RATE))

        # compute segment lengths in samples, clamping so they sum to total_samples
        attack_samples = min(int(self.attack * SAMPLE_RATE), total_samples)
        decay_samples = min(int(self.decay * SAMPLE_RATE), max(0, total_samples - attack_samples))
        release_samples = min(int(self.release * SAMPLE_RATE), max(0, total_samples - attack_samples - decay_samples))

        sustain_samples = max(0, total_samples - attack_samples - decay_samples - release_samples)

        envelope = np.zeros(total_samples)

        idx = 0

        # 1. Attack (0 to 1)
        if attack_samples > 0:
            envelope[idx:idx + attack_samples] = np.linspace(0, 1, attack_samples)
            idx += attack_samples

        # 2. Decay (1 to Sustain Level)
        if decay_samples > 0 and idx < total_samples:
            env_start = envelope[idx - 1] if idx > 0 else 1.0
            write_len = min(decay_samples, total_samples - idx)
            envelope[idx:idx + write_len] = np.linspace(env_start, self.sustain, write_len)
            idx += write_len

        # 3. Sustain (Sustain Level)
        if sustain_samples > 0 and idx < total_samples:
            write_len = min(sustain_samples, total_samples - idx)
            envelope[idx:idx + write_len] = self.sustain
            idx += write_len

        # 4. Release (Sustain Level to 0)
        if release_samples > 0 and idx < total_samples:
            env_start = envelope[idx - 1] if idx > 0 else self.sustain
            write_len = min(release_samples, total_samples - idx)
            envelope[idx:idx + write_len] = np.linspace(env_start, 0, write_len)
            idx += write_len

        # If any samples remain (due to rounding), fill with 0
        if idx < total_samples:
            envelope[idx:] = 0.0

        return envelope