from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import pytz
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()  # Load variables from .env

#Fixe the date time to EST Jamaica timezone 
# Choose your target timezone
# TARGET_TZ = pytz.timezone('America/New_York') # Handles DST (EST/EDT)
TARGET_TZ = pytz.timezone('America/Jamaica') # Fixed EST (UTC-5), suitable for Kingston

def get_current_time_in_target_tz():
    """Gets the current time localized to the target timezone."""
    return datetime.now(TARGET_TZ)


# --- Pydantic Models ---

class TemperatureReading(BaseModel):
    sensor_id: str
    sensor_name: str
    temperature: float
    sensor_type: str  # DS18B20 or TMP36
    battery_level: Optional[float] = None  # only for NRF sensors
    timestamp: Optional[datetime] = datetime.now(TARGET_TZ)

class FanControl(BaseModel):
    fan_id: str  # cold_fan_1, cold_fan_2
    fan_name: str
    speed_percent: int

class PeltierControl(BaseModel):
    block_id: str  # peltier_block_1 or peltier_block_2
    state: bool

class SolarPVData(BaseModel):
    panel_voltage: float
    panel_current: float
    load_voltage: float
    load_current: float
    load_power: float
    battery_voltage: float
    battery_current: float
    sunlight_intensity: float
    timestamp: Optional[datetime] = datetime.now(TARGET_TZ)

# --- Data Storage ---
temp_data: List[TemperatureReading] = []
fan_states = {"cold_fan_1": 0, "cold_fan_2": 0}
peltier_blocks = {"peltier_block_1": False, "peltier_block_2": False}
pump_states = {"pump_1": False, "pump_2": False}
hot_fan_pid_outputs = {"hot_fan_1": 0, "hot_fan_2": 0}  # simulated PID values
solar_pv_logs: List[SolarPVData] = []

# --- API Endpoints ---

@app.post("/temperature")
async def receive_temperature(data: List[TemperatureReading]):
    temp_data.extend(data)
    return {"message": "Temperature data received.", "count": len(data)}

@app.put("/fan_control")
async def update_fan_speed(control: FanControl):
    if control.fan_id not in fan_states:
        raise HTTPException(status_code=404, detail="Fan not found")
    fan_states[control.fan_id] = control.speed_percent
    return {"message": f"Fan {control.fan_id} speed updated.", "speed": control.speed_percent}

@app.post("/peltier_control")
async def set_peltier_state(control: PeltierControl):
    if control.block_id not in peltier_blocks:
        raise HTTPException(status_code=404, detail="Peltier block not found")

    peltier_blocks[control.block_id] = control.state
    block_index = 1 if control.block_id.endswith("1") else 2
    pump_states[f"pump_{block_index}"] = control.state
    fan_states[f"cold_fan_{block_index}"] = 100 if control.state else 0
    hot_fan_pid_outputs[f"hot_fan_{block_index}"] = 100 if control.state else 0  # simulate PID output

    return {"message": f"Peltier block {control.block_id} {'ON' if control.state else 'OFF'}"}

@app.post("/solar_pv")
async def receive_solar_data(data: SolarPVData):
    solar_pv_logs.append(data)
    return {"message": "Solar PV data received."}

@app.get("/status")
def get_system_status():
    return {
        "temperatures": [t.dict() for t in temp_data[-8:]],  # latest 8 readings
        "fan_states": fan_states,
        "peltier_blocks": peltier_blocks,
        "pump_states": pump_states,
        "hot_fan_pid_outputs": hot_fan_pid_outputs,
        "solar_data": solar_pv_logs[-1].dict() if solar_pv_logs else {}
    }


if __name__ == "__app__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

#uvicorn main:app --host 0.0.0.0 --port 8000 ALWAYS STARTS THE SERVER