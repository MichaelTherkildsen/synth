from Modules.Libs.libs import *
import numpy as np

class Filter:
    """Manages IIR digital filtering operations (Low-pass, High-pass, Band-pass)."""
    def __init__(self, filter_type, cutoff, resonance):
        self.type = filter_type
        self.cutoff = cutoff
        self.resonance = resonance # Q

    def apply(self, data, order=2, cutoff_envelope=None):
        """Apply filter to data.

        If cutoff_envelope is provided (array of per-sample cutoff frequencies), and
        the filter type is Low-pass, a simple time-varying one-pole low-pass is applied
        sample-by-sample. For other cases the static IIR butterworth implementation is used.
        """
        if self.type == "None":
            return data

        nyquist = SAMPLE_RATE / 2
        Q = self.resonance
        scaled_order = int(max(1, order * Q))

        # Time-varying low-pass using one-pole filter (cheap and stable)
        if cutoff_envelope is not None and self.type == "Low-pass":
            # ensure envelope length matches data
            env = np.asarray(cutoff_envelope)
            if env.shape[0] != data.shape[0]:
                # try to resample or truncate/pad to match
                minlen = min(env.shape[0], data.shape[0])
                if env.shape[0] < data.shape[0]:
                    # pad last value
                    env = np.concatenate([env, np.full(data.shape[0] - env.shape[0], env[-1])])
                else:
                    env = env[:data.shape[0]]

            # clamp
            env = np.clip(env, 20.0, MAX_FREQ)

            # compute per-sample alpha for one-pole filter
            # alpha = 1 - exp(-2*pi*fc / fs)
            alpha = 1.0 - np.exp(-2.0 * np.pi * (env / float(SAMPLE_RATE)))

            # apply one-pole filter
            y = np.zeros_like(data)
            if data.size == 0:
                return data
            y[0] = data[0]
            for n in range(1, data.shape[0]):
                a = alpha[n]
                y[n] = y[n-1] + a * (data[n] - y[n-1])
            return y

        # fallback to static IIR filters
        if self.type == "Low-pass":
            cutoff = clamp(self.cutoff, 20, MAX_FREQ)
            normal_cutoff = cutoff / nyquist
            b, a = butter(scaled_order, normal_cutoff, btype='low', analog=False)
            return lfilter(b, a, data)

        elif self.type == "High-pass":
            cutoff = clamp(self.cutoff, 20, MAX_FREQ)
            normal_cutoff = cutoff / nyquist
            b, a = butter(scaled_order, normal_cutoff, btype='high', analog=False)
            return lfilter(b, a, data)

        elif self.type == "Band-pass":
            # Using the original code's approach: high_cutoff = cutoff * 1.5
            low_cutoff = clamp(self.cutoff, 20, MAX_FREQ)
            high_cutoff = clamp(low_cutoff * 1.5, low_cutoff, MAX_FREQ)

            low = low_cutoff / nyquist
            high = high_cutoff / nyquist

            # Applying Q to bandwidth
            bandwidth = high - low
            scaled_bandwidth = bandwidth / Q

            low_limit = clamp(low - scaled_bandwidth / 2, 0.01, 0.99)
            high_limit = clamp(high + scaled_bandwidth / 2, low_limit, 0.99)

            b, a = butter(scaled_order, [low_limit, high_limit], btype='band', analog=False)
            return lfilter(b, a, data)

        return data