import customtkinter as ctk
from functools import partial
import threading
import numpy as np
import sounddevice as sd
from scipy.signal import butter, lfilter

from Modules.utils import note_to_frequency, normalize_wave, play_wave_dynamic, SAMPLE_RATE, MAX_FREQ, clamp
from Modules.voice import Voice
from Modules.adsr import ADSR
from Modules.filter import Filter
from Modules.oscillator import Oscillator