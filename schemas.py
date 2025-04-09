# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import pytz # If using timezone support
import os


# Example using the timezone function from previous steps
TARGET_TZ = pytz.timezone('America/Jamaica')
def get_current_time_in_target_tz():
   return datetime.now(TARGET_TZ)

# Schema for receiving temperature data in requests
# (Might not need timestamp here if DB generates it)
# schemas.py
class TemperatureReadingBase(BaseModel):
    sensor_id: str
    sensor_name: Optional[str] = None # <-- Make optional, default to None
    temperature: float
    sensor_type: str
    battery_level: Optional[float] = None

# Schema for creating data (use this in the endpoint now)
class TemperatureReadingCreate(TemperatureReadingBase):
    pass

# Schema for reading/returning data (still includes fields from DB model)
class TemperatureReading(TemperatureReadingBase):
    id: int
    timestamp: datetime
    # Ensure sensor_name is Optional here too if it inherits, or handle None display
    sensor_name: Optional[str] = None # Match Base

    class Config:
        from_attributes = True # Use this instead of orm_mode

# Define schemas for FanControl, PeltierControl, SolarPVData similarly...
class FanControl(BaseModel):
    fan_id: str
    speed_percent: int

class PeltierControl(BaseModel):
    block_id: str
    state: bool

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
     pass

class SolarPVData(SolarPVDataBase):
     id: int
     timestamp: datetime

     class Config:
        from_attributes = True # Changed from orm_mode