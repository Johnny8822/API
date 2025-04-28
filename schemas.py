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
    # If ON/OFF status is sent WITH readings, add them here too
    # fan_1_status: Optional[bool] = None
    # ... other status fields

class SolarPVDataBase(BaseModel):
    panel_voltage: float
    panel_current: float
    battery_voltage: float
    battery_current: float
    load_voltage: float
    load_current: float
    load_power: float
    sunlight_intensity: float

# SettingsBase schema - should contain ALL fields from the model (editable + status)
class SettingsBase(BaseModel):
    temperature_setpoint: Optional[float] = Field(None, ge=-50, le=150) # Adjusted range
    ac_timer_on: Optional[time] = None
    ac_timer_off: Optional[time] = None
    # Renamed Fan 1 field (Block 1 Cold side speed - CONTROLLABLE)
    fan_4_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    # Fan 2 (Block 2 Cold side speed - CONTROLLABLE)
    fan_2_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    # Fan 3 speed (Block 2 Hot side speed - REPORTING ONLY)
    fan_3_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    # Fan 1 speed (Block 1 Hot side speed - REPORTING ONLY)
    fan_1_speed_percent: Optional[int] = Field(None, ge=0, le=100) # Added Fan 1 speed reporting field


    # Add status fields to the Base schema
    fan_1_status: Optional[bool] = None # Block 1 Hot Fan status
    fan_4_status: Optional[bool] = None # Block 1 Cold Fan status
    pump_1_status: Optional[bool] = None # Block 1 Pump status
    peltier_1_status: Optional[bool] = None # Block 1 Peltier status

    fan_3_status: Optional[bool] = None # Block 2 Hot Fan status
    fan_2_status: Optional[bool] = None # Block 2 Cold Fan status
    pump_2_status: Optional[bool] = None # Block 2 Pump status
    peltier_2_status: Optional[bool] = None # Block 2 Peltier status

    updated_at: Optional[datetime] = None

# --- CREATE Schemas (remain similar, based on what you send from ESP32) ---
class TemperatureReadingCreate(TemperatureReadingBase):
    pass # Add status fields here if ESP32 sends them with readings

class SolarPVDataCreate(SolarPVDataBase):
     pass

# --- RESPONSE/READ Schemas ---
class TemperatureReading(TemperatureReadingBase): # Inherits from Base defined above
    id: int
    timestamp: datetime
    # If status is part of the reading, add it here too

    class Config:
        from_attributes = True

class SolarPVData(SolarPVDataBase): # Inherits from Base defined above
     id: int
     timestamp: datetime

     class Config:
        from_attributes = True

# SettingsUpdate schema - should only contain fields that can be UPDATED via PATCH
# Status fields and non-controllable speeds are NOT included here.
class SettingsUpdate(BaseModel):
    temperature_setpoint: Optional[float] = Field(None, ge=-50, le=150)
    ac_timer_on: Optional[time] = None
    ac_timer_off: Optional[time] = None
    # Controllable Fan speeds
    fan_4_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    fan_2_speed_percent: Optional[int] = Field(None, ge=0, le=100)
    # Fan 1 and 3 speeds are NOT in SettingsUpdate as they are PID controlled, not set from UI


# Settings schema (for GET response) - includes ALL fields from the model (editable + status)
class Settings(SettingsBase): # Inherits all fields, including status and reporting speeds
    id: int
    # updated_at is already in SettingsBase

    class Config:
        from_attributes = True

# --- Other schemas ---
# SystemStatus schema - Includes all fields from the updated Settings model
class SystemStatus(BaseModel):
    temperatures: List[TemperatureReading]
    solar_data: Optional[SolarPVData] = None
    # current_settings now includes all fields from the Settings model, including status and reporting speeds
    current_settings: Optional[Settings] = None

    class Config:
        from_attributes = True