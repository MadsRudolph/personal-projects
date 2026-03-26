import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from device import device_manager
from scope import scope
from wavegen import wavegen

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScopeConfig(BaseModel):
    ch1_range: float | None = None
    ch2_range: float | None = None
    ch1_enabled: bool | None = None
    ch2_enabled: bool | None = None
    trigger_source: str | None = None
    trigger_level: float | None = None
    trigger_edge: str | None = None
    trigger_mode: str | None = None
    sample_rate: float | None = None
    time_per_div: float | None = None

class WaveGenConfig(BaseModel):
    waveform: str | None = None
    frequency: float | None = None
    amplitude: float | None = None
    offset: float | None = None
    duty_cycle: float | None = None
    sweep_enabled: bool | None = None
    sweep_start: float | None = None
    sweep_stop: float | None = None
    sweep_time: float | None = None
    am_enabled: bool | None = None
    am_frequency: float | None = None
    am_depth: float | None = None
    fm_enabled: bool | None = None
    fm_frequency: float | None = None
    fm_deviation: float | None = None
    dc_output: bool | None = None
    dc_voltage: float | None = None

@app.post("/connect")
def connect_device():
    return device_manager.connect()

@app.post("/disconnect")
def disconnect_device():
    device_manager.disconnect()
    return {"ok": True}

@app.get("/status")
def device_status():
    return {"connected": device_manager.connected}

@app.post("/scope/configure")
def configure_scope(config: ScopeConfig):
    for field, value in config.model_dump(exclude_none=True).items():
        setattr(scope, field, value)
    if device_manager.connected:
        scope.configure()
    return {"ok": True}

@app.post("/scope/autoscale")
def autoscale():
    if not device_manager.connected:
        return {"ok": False, "error": "Not connected"}
    result = scope.autoscale()
    return {"ok": True, **result}

@app.post("/scope/start")
def start_scope():
    scope.start()
    return {"ok": True}

@app.post("/scope/stop")
def stop_scope():
    scope.stop()
    return {"ok": True}

@app.websocket("/ws/scope")
async def scope_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            if scope.running and device_manager.connected:
                data = await asyncio.to_thread(scope.acquire_single)
                if data:
                    await websocket.send_json(data)
            await asyncio.sleep(0.016)
    except WebSocketDisconnect:
        pass

@app.post("/wavegen/configure")
def configure_wavegen(config: WaveGenConfig):
    for field, value in config.model_dump(exclude_none=True).items():
        setattr(wavegen, field, value)
    wavegen.configure()
    return {"ok": True}

@app.post("/wavegen/enable")
def enable_wavegen():
    wavegen.enable()
    return {"ok": True}

@app.post("/wavegen/disable")
def disable_wavegen():
    wavegen.disable()
    return {"ok": True}

@app.get("/wavegen/state")
def wavegen_state():
    return {
        "enabled": wavegen.enabled,
        "waveform": wavegen.waveform,
        "frequency": wavegen.frequency,
        "amplitude": wavegen.amplitude,
        "offset": wavegen.offset,
        "duty_cycle": wavegen.duty_cycle,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
