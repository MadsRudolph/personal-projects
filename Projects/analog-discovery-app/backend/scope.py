import numpy as np
from ctypes import *
from device import dwf, device_manager
from dwfconstants import *
import time

BUFFER_SIZE = 4000

class ScopeController:
    def __init__(self):
        self.running = False
        self.sample_rate = 20_000_000.0
        self.buffer_size = BUFFER_SIZE
        self.ch1_range = 5.0
        self.ch2_range = 5.0
        self.ch1_enabled = True
        self.ch2_enabled = True
        self.trigger_source = "ch1"
        self.trigger_level = 0.0
        self.trigger_edge = "rising"
        self.trigger_mode = "auto"
        self.time_per_div = 0.001
        self._ch1_buffer = (c_double * BUFFER_SIZE)()
        self._ch2_buffer = (c_double * BUFFER_SIZE)()

    def configure(self):
        hdwf = device_manager.handle
        dwf.FDwfAnalogInFrequencySet(hdwf, c_double(self.sample_rate))
        dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(self.buffer_size))
        dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_int(1 if self.ch1_enabled else 0))
        dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(1), c_int(1 if self.ch2_enabled else 0))
        dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(self.ch1_range))
        dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(self.ch2_range))
        dwf.FDwfAnalogInChannelFilterSet(hdwf, c_int(-1), filterDecimate)
        if self.trigger_mode == "auto":
            dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn)
            dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(1.0))
        elif self.trigger_mode == "normal":
            dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn)
            dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0.0))
        else:
            dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn)
            dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0.0))
        ch = c_int(0) if self.trigger_source == "ch1" else c_int(1)
        dwf.FDwfAnalogInTriggerChannelSet(hdwf, ch)
        dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(self.trigger_level))
        edge = trigcondRisingPositive if self.trigger_edge == "rising" else trigcondFallingNegative
        dwf.FDwfAnalogInTriggerConditionSet(hdwf, edge)
        dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(0))

    def start(self):
        self.configure()
        self.running = True

    def stop(self):
        self.running = False

    def acquire_single(self) -> dict | None:
        if not device_manager.connected:
            return None
        hdwf = device_manager.handle
        sts = c_byte()
        dwf.FDwfAnalogInConfigure(hdwf, c_int(0), c_int(1))
        for _ in range(100):
            dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value:
                break
            time.sleep(0.001)
        else:
            if self.trigger_mode != "auto":
                return None
        result = {"ch1": None, "ch2": None}
        if self.ch1_enabled:
            dwf.FDwfAnalogInStatusData(hdwf, c_int(0), self._ch1_buffer, self.buffer_size)
            result["ch1"] = np.frombuffer(self._ch1_buffer, dtype=np.float64).tolist()
        if self.ch2_enabled:
            dwf.FDwfAnalogInStatusData(hdwf, c_int(1), self._ch2_buffer, self.buffer_size)
            result["ch2"] = np.frombuffer(self._ch2_buffer, dtype=np.float64).tolist()
        result["measurements"] = self._compute_measurements(result)
        result["sample_rate"] = self.sample_rate
        result["buffer_size"] = self.buffer_size
        return result

    def _compute_measurements(self, data: dict) -> dict:
        measurements = {}
        for ch_name in ["ch1", "ch2"]:
            if data[ch_name] is None:
                continue
            arr = np.array(data[ch_name])
            vpp = float(np.max(arr) - np.min(arr))
            mean = float(np.mean(arr))
            vmax = float(np.max(arr))
            vmin = float(np.min(arr))
            freq = self._estimate_frequency(arr, self.sample_rate)
            measurements[ch_name] = {
                "vpp": round(vpp, 4),
                "mean": round(mean, 4),
                "max": round(vmax, 4),
                "min": round(vmin, 4),
                "frequency": round(freq, 2) if freq else None,
            }
        return measurements

    def _estimate_frequency(self, data: np.ndarray, sample_rate: float) -> float | None:
        mean = np.mean(data)
        centered = data - mean
        crossings = np.where(np.diff(np.sign(centered)))[0]
        if len(crossings) < 2:
            return None
        avg_period_samples = np.mean(np.diff(crossings)) * 2
        if avg_period_samples == 0:
            return None
        return sample_rate / avg_period_samples

    def autoscale(self) -> dict:
        hdwf = device_manager.handle
        dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(-1), c_double(25.0))
        dwf.FDwfAnalogInFrequencySet(hdwf, c_double(20_000_000.0))
        dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(BUFFER_SIZE))
        dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn)
        dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0.5))
        dwf.FDwfAnalogInConfigure(hdwf, c_int(1), c_int(1))
        sts = c_byte()
        for _ in range(200):
            dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
            if sts.value == DwfStateDone.value:
                break
            time.sleep(0.005)
        buf = (c_double * BUFFER_SIZE)()
        dwf.FDwfAnalogInStatusData(hdwf, c_int(0), buf, BUFFER_SIZE)
        arr = np.frombuffer(buf, dtype=np.float64)
        vpp = float(np.max(arr) - np.min(arr))
        freq = self._estimate_frequency(arr, 20_000_000.0)
        volts_per_div_options = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        target_range = vpp * 1.2
        volts_per_div = 5.0
        for vpd in volts_per_div_options:
            if vpd * 8 >= target_range:
                volts_per_div = vpd
                break
        time_per_div = 0.001
        if freq and freq > 0:
            period = 1.0 / freq
            total_time = period * 2.5
            time_per_div = total_time / 10.0
        trigger_level = float(np.mean(arr))
        self.ch1_range = volts_per_div * 8
        self.ch2_range = volts_per_div * 8
        self.trigger_level = trigger_level
        if freq:
            self.sample_rate = min(100_000_000, max(1000, freq * self.buffer_size / 2.5))
        self.time_per_div = time_per_div
        self.configure()
        return {
            "volts_per_div": volts_per_div,
            "time_per_div": time_per_div,
            "trigger_level": trigger_level,
            "detected_frequency": freq,
            "detected_vpp": vpp,
        }

scope = ScopeController()
