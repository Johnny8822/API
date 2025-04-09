# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from database import Base # Import Base from your database.py
from datetime import datetime
import pytz # If using timezone support

# Example using the timezone function from previous steps
TARGET_TZ = pytz.timezone('America/Jamaica')
def get_current_time_in_target_tz():
   return datetime.now(TARGET_TZ)

# Maps to a 'temperature_readings' table in your database
class TemperatureReadingDB(Base):
    __tablename__ = "temperature_readings"

    id = Column(Integer, primary_key=True, index=True) # Auto-incrementing primary key
    sensor_id = Column(String, index=True)
    sensor_name = Column(String)
    temperature = Column(Float)
    sensor_type = Column(String)
    battery_level = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=get_current_time_in_target_tz) # Use your TZ function

# Define classes for your other data types similarly (e.g., SolarPVDataDB)
# class SolarPVDataDB(Base):
#    __tablename__ = "solar_pv_data"
#    id = Column(Integer, primary_key=True, index=True)
#    panel_voltage = Column(Float)
#    # ... other columns corresponding to your SolarPVData Pydantic model
#    timestamp = Column(DateTime, default=get_current_time_in_target_tz)