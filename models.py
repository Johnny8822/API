# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Time
from datetime import datetime, time
import pytz

# --- CORRECTED IMPORT ---
from database import Base # Use absolute import
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
   timestamp = Column(DateTime(timezone=True), default=get_current_time_in_target_tz)

# System Settings Model
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    temperature_setpoint = Column(Float, default=23.0)
    ac_timer_on = Column(Time, default=time(hour=7, minute=0))
    ac_timer_off = Column(Time, default=time(hour=22, minute=0))
    fan_1_speed_percent = Column(Integer, default=50)
    fan_2_speed_percent = Column(Integer, default=50)
    updated_at = Column(DateTime(timezone=True), default=get_current_time_in_target_tz, onupdate=get_current_time_in_target_tz)