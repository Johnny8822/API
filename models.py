# models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Time
from datetime import datetime, time
import pytz

# --- CORRECTED IMPORT ---
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


# System Settings Model - UPDATED
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)

    # Editable Parameters (Controllable from UI)
    temperature_setpoint = Column(Float, default=23.0, nullable=True) # Make nullable if not always required
    ac_timer_on = Column(Time, default=time(hour=7, minute=0), nullable=True)
    ac_timer_off = Column(Time, default=time(hour=22, minute=0), nullable=True)
    # Renamed Fan 1 speed to Fan 4 speed (Block 1 Cold side speed control)
    fan_4_speed_percent = Column(Integer, default=50, nullable=True) # Make nullable if not always required
    # Fan 2 speed (Block 2 Cold side speed control)
    fan_2_speed_percent = Column(Integer, default=50, nullable=True)
    # Fan 3 speed (Block 2 Hot side - controlled by PID, speed might be reported but not set here)
    fan_3_speed_percent = Column(Integer, default=50, nullable=True)
    # Fan 1 speed (Block 1 Hot side - controlled by PID, speed might be reported but not set here)
    fan_1_speed_percent = Column(Integer, default=50, nullable=True) # Added Fan 1 speed reporting field


    # Add fields for live ON/OFF status (Assuming boolean, nullable if status isn't always sent)
    # These statuses are controlled by ESP32 block pins, but we track them individually
    # Block 1 Components
    fan_1_status = Column(Boolean, default=False, nullable=True) # Status for Fan 1 (Block 1 Hot side)
    fan_4_status = Column(Boolean, default=False, nullable=True) # Status for Fan 4 (Block 1 Cold side)
    pump_1_status = Column(Boolean, default=False, nullable=True) # Status for Pump 1
    peltier_1_status = Column(Boolean, default=False, nullable=True) # Status for Peltier Block 1

    # Block 2 Components
    fan_3_status = Column(Boolean, default=False, nullable=True) # Status for Fan 3 (Block 2 Hot side)
    fan_2_status = Column(Boolean, default=False, nullable=True) # Status for Fan 2 (Block 2 Cold side)
    pump_2_status = Column(Boolean, default=False, nullable=True) # Status for Pump 2
    peltier_2_status = Column(Boolean, default=False, nullable=True) # Status for Peltier Block 2

    # Timestamp for when these settings/status were last updated
    updated_at = Column(DateTime(timezone=True), default=get_current_time_in_target_tz, onupdate=get_current_time_in_target_tz)