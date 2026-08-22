"""Shared AD3 helpers for caliper bring-up.

WHY THE ANALOG SCOPE AND NOT THE LOGIC ANALYZER
-----------------------------------------------
The caliper's data port swings 0 -> ~1.5 V. The AD3's 16 DIO logic-analyzer
inputs are fixed 3.3 V LVCMOS: their guaranteed logic-high threshold is about
2.0 V, and this device exposes no adjustable logic level (checked at runtime --
`DwfDeviceParameter` on this build has no DigitalVoltage member, and analogIO
offers only V+, V-, System Monitor and Power). A 1.5 V high therefore reads as
a steady LOW and the lines look dead.

So we use the two ANALOG scope channels instead. They are 14-bit, high
impedance, and utterly happy at 1.5 V. Two channels is exactly what the
protocol needs: CLK and DATA.

WIRING
------
  AD3 GND (black)  -> caliper battery NEGATIVE      <- the only hard reference
  Scope 1- (white/orange stripe) -> same battery negative
  Scope 2- (white/blue stripe)   -> same battery negative
  Scope 1+ (orange) -> pad under test
  Scope 2+ (blue)   -> pad under test

Scope inputs are ~1 Mohm and read-only, so touching an unknown pad cannot hurt
the caliper. The one thing NOT to do is clip the black GND lead to a pad before
you know which pad is ground.

Close the WaveForms GUI first -- only one application can own the AD3.
"""

import time

import numpy as np
from pydwf import DwfLibrary, DwfAcquisitionMode, DwfState
from pydwf.utilities import openDwfDevice

# AD3 analog input: smallest range is 5 V full-scale (+/-2.5 V), plenty of
# headroom and resolution for a 1.5 V logic swing.
RANGE_V = 5.0

DEVICE_BUSY_HINTS = ("another application", "djtgenable", "jtag init")


class Ad3Busy(RuntimeError):
    """Raised when the AD3 is held by the WaveForms GUI or another process."""


def open_ad3():
    """Open the AD3, turning the 'device busy' failure into a clear message."""
    try:
        return openDwfDevice(DwfLibrary())
    except Exception as exc:
        if any(h in str(exc).lower() for h in DEVICE_BUSY_HINTS):
            raise Ad3Busy(
                "AD3 is in use -- close the WaveForms GUI first."
            ) from exc
        raise


def _configure_scope(ain, rate_hz, channels):
    ain.reset()
    for ch in range(ain.channelCount()):
        enabled = ch in channels
        ain.channelEnableSet(ch, enabled)
        if enabled:
            ain.channelRangeSet(ch, RANGE_V)
            ain.channelOffsetSet(ch, 0.0)
    ain.frequencySet(rate_hz)
    return ain.frequencyGet()


def record(device, rate_hz, seconds, channels=(0, 1)):
    """Stream the scope channels for `seconds`.

    Record mode streams over USB, so the capture length is bounded by time
    rather than by the 16384-sample on-device buffer. That matters here: the
    caliper emits a frame only a few times a second, so a single-shot buffer
    would usually catch nothing.

    Returns (data, actual_rate, lost, corrupt) where data is a dict
    {channel: float32 array of volts}.
    """
    channels = tuple(channels)
    ain = device.analogIn
    actual_rate = _configure_scope(ain, rate_hz, channels)

    ain.acquisitionModeSet(DwfAcquisitionMode.Record)
    ain.recordLengthSet(seconds)
    ain.configure(False, True)

    chunks = {ch: [] for ch in channels}
    lost_total = corrupt_total = 0

    # Wait for the acquisition to actually start before we begin timing.
    t0 = time.time()
    while True:
        st = ain.status(True)
        if st in (DwfState.Triggered, DwfState.Running, DwfState.Done):
            break
        if time.time() - t0 > 3.0:
            break
        time.sleep(0.001)

    t0 = time.time()
    # Allow a little slack over the requested window so recordLength can finish.
    deadline = t0 + seconds + 2.0
    while time.time() < deadline:
        st = ain.status(True)
        available, lost, corrupt = ain.statusRecord()
        lost_total += lost
        corrupt_total += corrupt
        if available == 0:
            if st == DwfState.Done:
                break
            time.sleep(0.0005)
            continue
        # Read every channel with the SAME `available` count, before the next
        # status() call moves the record pointer on.
        for ch in channels:
            chunks[ch].append(
                np.asarray(ain.statusData(ch, available), dtype=np.float32)
            )
        if st == DwfState.Done:
            break

    data = {
        ch: (np.concatenate(chunks[ch]) if chunks[ch]
             else np.empty(0, np.float32))
        for ch in channels
    }
    return data, actual_rate, lost_total, corrupt_total


def swing(volts, pct=0.2):
    """Robust low/high levels of a trace, as (lo, hi).

    Deliberately NOT the 5th/95th percentile. The caliper transmits for only a
    few percent of the time, so on the DATA line the 95th percentile is still
    the idle level and the swing appears to be zero. Reaching further into the
    tails catches a signal that is high for as little as `pct` percent of the
    window, while still ignoring single-sample spikes.
    """
    if volts.size == 0:
        return 0.0, 0.0
    lo, hi = np.percentile(volts, [pct, 100.0 - pct])
    return float(lo), float(hi)


def digitize(volts, threshold=None, min_swing=0.20):
    """Slice an analog trace into logic levels.

    The threshold is the midpoint of the robust range from swing(). Two things
    that look smarter are worse here:

    * 5th/95th percentiles miss the swing entirely, because the caliper is idle
      for most of the window.
    * Otsu's method puts the threshold right on top of the minority level when
      the duty cycle is lopsided -- measured at 76 mV on a 1.5 V clock that is
      low only 4% of the time, close enough to the noise floor that stray
      excursions became extra clock edges and shifted whole frames.

    A trace whose range is under `min_swing` is treated as static and returns
    all-zeros, so an idle line cannot produce edges at all.
    """
    if volts.size == 0:
        return np.empty(0, np.int8), 0.0
    if threshold is None:
        lo, hi = swing(volts)
        if hi - lo < min_swing:
            # Static line: put the threshold out of reach so nothing toggles.
            return np.zeros(volts.size, np.int8), float(volts.max()) + 1.0
        threshold = 0.5 * (lo + hi)
    return (volts > threshold).astype(np.int8), float(threshold)


def edge_indices(bits):
    """Indices i where bits[i] differs from bits[i-1]."""
    if bits.size < 2:
        return np.empty(0, np.int64)
    return np.flatnonzero(np.diff(bits)) + 1


def find_bursts(bits, rate_hz, gap_s):
    """Group edges into bursts separated by at least `gap_s` of quiet.

    This is how frames get framed: the caliper has no preamble, only silence
    between frames. Returns a list of (start_index, end_index) sample spans.
    """
    edges = edge_indices(bits)
    if edges.size == 0:
        return []
    gap_samples = max(1, int(round(gap_s * rate_hz)))
    splits = np.flatnonzero(np.diff(edges) > gap_samples)
    starts = np.concatenate(([0], splits + 1))
    ends = np.concatenate((splits, [edges.size - 1]))
    return [(int(edges[s]), int(edges[e])) for s, e in zip(starts, ends)]
