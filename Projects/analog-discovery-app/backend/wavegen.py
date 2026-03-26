from ctypes import *
from device import dwf, device_manager
from dwfconstants import *

WAVEFORM_MAP = {
    "sine": funcSine,
    "square": funcSquare,
    "triangle": funcTriangle,
    "sawtooth": funcRampUp,
}

class WaveGenController:
    def __init__(self):
        self.channel = 0
        self.enabled = False
        self.waveform = "sine"
        self.frequency = 1000.0
        self.amplitude = 1.0
        self.offset = 0.0
        self.duty_cycle = 50.0
        self.sweep_enabled = False
        self.sweep_start = 100.0
        self.sweep_stop = 10000.0
        self.sweep_time = 0.01
        self.am_enabled = False
        self.am_frequency = 100.0
        self.am_depth = 50.0
        self.fm_enabled = False
        self.fm_frequency = 100.0
        self.fm_deviation = 1000.0
        self.dc_output = False
        self.dc_voltage = 0.0

    def configure(self):
        if not device_manager.connected:
            return
        hdwf = device_manager.handle
        ch = c_int(self.channel)

        if self.dc_output:
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeCarrier, c_int(1))
            dwf.FDwfAnalogOutNodeFunctionSet(hdwf, ch, AnalogOutNodeCarrier, funcDC)
            dwf.FDwfAnalogOutNodeOffsetSet(hdwf, ch, AnalogOutNodeCarrier, c_double(self.dc_voltage))
            dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, ch, AnalogOutNodeCarrier, c_double(0))
            dwf.FDwfAnalogOutConfigure(hdwf, ch, c_int(1))
            return

        func = WAVEFORM_MAP.get(self.waveform, funcSine)
        dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeCarrier, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, ch, AnalogOutNodeCarrier, func)
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, ch, AnalogOutNodeCarrier, c_double(self.frequency))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, ch, AnalogOutNodeCarrier, c_double(self.amplitude))
        dwf.FDwfAnalogOutNodeOffsetSet(hdwf, ch, AnalogOutNodeCarrier, c_double(self.offset))

        if self.waveform == "square":
            dwf.FDwfAnalogOutNodeSymmetrySet(hdwf, ch, AnalogOutNodeCarrier, c_double(self.duty_cycle))

        if self.sweep_enabled:
            mid_freq = (self.sweep_start + self.sweep_stop) / 2
            dwf.FDwfAnalogOutNodeFrequencySet(hdwf, ch, AnalogOutNodeCarrier, c_double(mid_freq))
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeFM, c_int(1))
            dwf.FDwfAnalogOutNodeFunctionSet(hdwf, ch, AnalogOutNodeFM, funcRampUp)
            dwf.FDwfAnalogOutNodeFrequencySet(hdwf, ch, AnalogOutNodeFM, c_double(1.0 / self.sweep_time))
            deviation = 100.0 * (self.sweep_stop - mid_freq) / mid_freq
            dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, ch, AnalogOutNodeFM, c_double(deviation))
            dwf.FDwfAnalogOutNodeSymmetrySet(hdwf, ch, AnalogOutNodeFM, c_double(100.0))
        elif self.fm_enabled:
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeFM, c_int(1))
            dwf.FDwfAnalogOutNodeFunctionSet(hdwf, ch, AnalogOutNodeFM, funcSine)
            dwf.FDwfAnalogOutNodeFrequencySet(hdwf, ch, AnalogOutNodeFM, c_double(self.fm_frequency))
            deviation_pct = 100.0 * self.fm_deviation / self.frequency
            dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, ch, AnalogOutNodeFM, c_double(deviation_pct))
        else:
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeFM, c_int(0))

        if self.am_enabled:
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeAM, c_int(1))
            dwf.FDwfAnalogOutNodeFunctionSet(hdwf, ch, AnalogOutNodeAM, funcSine)
            dwf.FDwfAnalogOutNodeFrequencySet(hdwf, ch, AnalogOutNodeAM, c_double(self.am_frequency))
            dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, ch, AnalogOutNodeAM, c_double(self.am_depth))
        else:
            dwf.FDwfAnalogOutNodeEnableSet(hdwf, ch, AnalogOutNodeAM, c_int(0))

        dwf.FDwfAnalogOutConfigure(hdwf, ch, c_int(1 if self.enabled else 0))

    def enable(self):
        self.enabled = True
        self.configure()

    def disable(self):
        self.enabled = False
        hdwf = device_manager.handle
        dwf.FDwfAnalogOutConfigure(hdwf, c_int(self.channel), c_int(0))

wavegen = WaveGenController()
