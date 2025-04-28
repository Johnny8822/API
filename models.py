# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Time
from datetime import datetime, time
import pytz

# --- CORRECTED IMPORT (Already looks good based on your code) ---
# Make sure this is an absolute import from your database.py file
from database import Base
# ----------------------

TARGET_TZ = pytz.timezone('America/Jamaica')
def get_current_time_in_target_tz():
    return datetime.now(TARGET_TZ)

# Maps to a 'temperature_readings' table in your database
class TemperatureReadingDB(Base):
    __tablename__ = "temperature_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    sensor_name = Column(String, nullable=True)
    temperature = Column(Float)
    sensor_type = Column(String)
    battery_level = Column(Float, nullable=True)
    # Ensure the DateTime column supports timezone
    timestamp = Column(DateTime(timezone=True), default=get_current_time_in_target_tz)

# Maps to a 'solar_pv_data' table
class SolarPVDataDB(Base):
    __tablename__ = "solar_pv_data"
    id = Column(Integer, primary_key=True, index=True)
    panel_voltage = Column(Float)
    panel_current = Column(Float)
    load_voltage = Column(Float)
    load_current = Column(Float)
    load_power = Column(Float)
    battery_voltage = Column(Float)
    battery_current = Column(Float)
    sunlight_intensity = Column(Float)
    # Ensure the DateTime column supports timezone
    timestamp = Column(DateTime(timezone=True), default=get_current_time_in_target_tz)

# System Settings Model
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    temperature_setpoint = Column(Float, default=23.0)
    ac_timer_on = Column(Time, default=time(hour=7, minute=0))
    ac_timer_off = Column(Time, default=time(hour=22, minute=0))
    # These fan speeds are included in the model definition
    fan_1_speed_percent = Column(Integer, default=50)
    fan_2_speed_percent = Column(Integer, default=50)
    # Note: Your database screenshot shows fan_3_speed_percent and fan_4_speed_percent
    # as well as status fields. This models.py *does not* include those based on the
    # specific file you uploaded. Let's use the models.py that matches the schema you showed.

    # --- UPDATED System Settings Model based on your database screenshot (7.png) ---
    # This version includes the columns shown in your database table.
    # If this is the model definition you are using, the error is very strange.
    # If your models.py file is actually *missing* these fields, that's the issue.
    # Assuming this is the correct definition you *intended* to be using:
    temperature_setpoint = Column(Float, default=23.0, nullable=True) # Match schema from screenshot if nullable
    ac_timer_on = Column(Time, default=time(hour=7, minute=0), nullable=True) # Match schema
    ac_timer_off = Column(Time, default=time(hour=22, minute=0), nullable=True) # Match schema
    fan_1_speed_percent = Column(Integer, default=50, nullable=True) # Match schema
    fan_2_speed_percent = Column(Integer, default=50, nullable=True) # Match schema
    fan_3_speed_percent = Column(Integer, default=50, nullable=True) # From screenshot
    fan_4_speed_percent = Column(Integer, default=50, nullable=True) # From screenshot

    # Status fields from screenshot
    fan_1_status = Column(Boolean, default=False, nullable=True) # From screenshot
    fan_4_status = Column(Boolean, default=False, nullable=True) # From screenshot
    pump_1_status = Column(Boolean, default=False, nullable=True) # From screenshot
    peltier_1_status = Column(Boolean, default=False, nullable=True) # From screenshot
    fan_3_status = Column(Boolean, default=False, nullable=True) # From screenshot
    fan_2_status = Column(Boolean, default=False, nullable=True) # From screenshot
    pump_2_status = Column(Boolean, default=False, nullable=True) # From screenshot
    peltier_2_status = Column(Boolean, default=False, nullable=True) # From screenshot


    # Ensure the DateTime column supports timezone
    updated_at = Column(DateTime(timezone=True), default=get_current_time_in_target_tz, onupdate=get_current_time_in_target_tz)