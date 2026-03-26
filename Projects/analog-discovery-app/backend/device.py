from ctypes import *
import sys

if sys.platform.startswith("win"):
    dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
    dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
else:
    dwf = cdll.LoadLibrary("libdwf.so")

from dwfconstants import *

class DeviceManager:
    def __init__(self):
        self.hdwf = c_int(0)
        self.connected = False

    def connect(self) -> dict:
        dwf.FDwfDeviceOpen(c_int(-1), byref(self.hdwf))
        if self.hdwf.value == hdwfNone.value:
            szerr = create_string_buffer(512)
            dwf.FDwfGetLastErrorMsg(szerr)
            return {"ok": False, "error": szerr.value.decode()}
        dwf.FDwfDeviceAutoConfigureSet(self.hdwf, c_int(0))
        self.connected = True
        return {"ok": True}

    def disconnect(self):
        if self.connected:
            dwf.FDwfDeviceCloseAll()
            self.connected = False
            self.hdwf = c_int(0)

    @property
    def handle(self):
        return self.hdwf

device_manager = DeviceManager()
