# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from database import Base # Import Base from your database.py
from datetime import datetime
import pytz # If using timezone support

TARGET_TZ = pytz.timezone('America/Jamaica')
def get_current_time_in_target_tz():
   return datetime.now(TARGET_TZ)

# Maps to a 'temperature_readings' table in your database
class TemperatureReadingDB(Base):
    __tablename__ = "temperature_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    sensor_name = Column(String, nullable=True) # Keep optional if needed
    temperature = Column(Float)
    sensor_type = Column(String)
    battery_level = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=get_current_time_in_target_tz)

# --- ADD OR UNCOMMENT THIS ---
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
   timestamp = Column(DateTime, default=get_current_time_in_target_tz)
# ----------------------------