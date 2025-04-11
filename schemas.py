# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import pytz

TARGET_TZ = pytz.timezone('America/Jamaica')
def get_current_time_in_target_tz():
   return datetime.now(TARGET_TZ)

# --- Temperature Schemas (ensure sensor_name is optional if needed) ---
class TemperatureReadingBase(BaseModel):
    sensor_id: str
    sensor_name: Optional[str] = None # Make optional
    temperature: float
    sensor_type: str
    battery_level: Optional[float] = None

class TemperatureReadingCreate(TemperatureReadingBase):
    pass

class TemperatureReading(TemperatureReadingBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Solar PV Schemas (ensure these are defined) ---
class SolarPVDataBase(BaseModel):
    panel_voltage: float
    panel_current: float
    load_voltage: float
    load_current: float
    load_power: float
    battery_voltage: float
    battery_current: float
    sunlight_intensity: float

class SolarPVDataCreate(SolarPVDataBase):
     pass # Use this for POST request body

class SolarPVData(SolarPVDataBase):
     id: int
     timestamp: datetime

     class Config:
        from_attributes = True # Use this for GET response (e.g., in status)

# --- Other Schemas (FanControl, PeltierControl if needed) ---
class FanControl(BaseModel):
    fan_id: str
    speed_percent: int

class PeltierControl(BaseModel):
    block_id: str
    state: bool

# --- ADD SCHEMA FOR STATUS RESPONSE ---
class SystemStatus(BaseModel):
    temperatures: List[TemperatureReading] # List of latest temp readings
    solar_data: Optional[SolarPVData] = None # Single latest solar reading (or None)
    fan_states: Optional[dict] = {} # Placeholder, replace if storing in DB
    peltier_blocks: Optional[dict] = {} # Placeholder
    pump_states: Optional[dict] = {} # Placeholder
    hot_fan_pid_outputs: Optional[dict] = {} # Placeholder

    class Config:
        from_attributes = True
# ------------------------------------