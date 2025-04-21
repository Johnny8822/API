# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, time
import pytz

# ... (Timezone stuff) ...

# --- Define BASE Schemas First ---
class TemperatureReadingBase(BaseModel):
    sensor_id: str
    sensor_name: Optional[str] = None
    temperature: float
    sensor_type: str
    battery_level: Optional[float] = None

class SolarPVDataBase(BaseModel):
    panel_voltage: float
    panel_current: float
    battery_voltage: float
    battery_current: float
    load_voltage: float 
    load_current: float
    load_power: float
    sunlight_intensity: float

class SettingsBase(BaseModel):
    # ... (settings fields) ...
    fan_2_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    fan_1_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    ac_timer_on: Optional[time] = None
    ac_timer_off: Optional[time] = None 
    temperature_setpoint: Optional[float] = Field(None, ge=0, le=100)
    updated_at: Optional[datetime] = None # Use datetime for updated_at
    
# --- Then define CREATE Schemas (if needed) ---
class TemperatureReadingCreate(TemperatureReadingBase):
    pass

class SolarPVDataCreate(SolarPVDataBase):
     pass

# --- Then define RESPONSE/READ Schemas ---
class TemperatureReading(TemperatureReadingBase): # Inherits from Base defined above
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class SolarPVData(SolarPVDataBase): # Inherits from Base defined above
     id: int
     timestamp: datetime

     class Config:
        from_attributes = True

class SettingsUpdate(SettingsBase): # Inherits from Base defined above
    pass

class Settings(SettingsBase): # Inherits from Base defined above
    id: int
    # ... (non-optional fields for response) ...
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Other schemas ---
class FanControl(BaseModel):
    fan_id: str
    speed_percent: int

class PeltierControl(BaseModel):
    block_id: str
    state: bool

class SystemStatus(BaseModel):
    temperatures: List[TemperatureReading]
    solar_data: Optional[SolarPVData] = None
    current_settings: Optional[Settings] = None

    class Config:
        from_attributes = True