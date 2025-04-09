# main.py (Simplified Example)
from fastapi import FastAPI, Depends, HTTPException, status # Added status
from sqlalchemy.orm import Session
from typing import List # Make sure List is imported


# Import your modules (adjust paths if needed)
import models
import schemas # Assuming your Pydantic models are in schemas.py
from database import engine, get_db
import psycopg2
# --- This line creates the tables in the database if they don't exist ---
# --- It uses the definitions from models.py ---
models.Base.metadata.create_all(bind=engine)
# -----------------------------------------------------------------------

app = FastAPI()

# Change the endpoint to accept a List of creation schemas
@app.post("/temperature", status_code=status.HTTP_201_CREATED) # Set default success code
async def receive_temperature(
    data: List[schemas.TemperatureReadingCreate], # Expect a LIST of creation objects
    db: Session = Depends(get_db)
):
    created_count = 0
    # Loop through each reading sent in the list
    for reading_data in data:
        # Create the DB model instance
        db_reading = models.TemperatureReadingDB(
           sensor_id=reading_data.sensor_id,
           # Use the sensor_name if provided, otherwise default (or handle as needed)
           sensor_name=reading_data.sensor_name or f"Sensor_{reading_data.sensor_id}",
           temperature=reading_data.temperature,
           sensor_type=reading_data.sensor_type,
           battery_level=reading_data.battery_level
        )
        db.add(db_reading)
        created_count += 1

    # Commit all readings added in the loop at once
    if created_count > 0:
        try:
            db.commit()
            # You generally don't need to refresh multiple items unless returning them
            return {"message": f"{created_count} temperature reading(s) saved successfully."}
        except Exception as e:
            db.rollback() # Rollback on error
            raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
    else:
         # If the input list was empty
         raise HTTPException(status_code=400, detail="No temperature readings provided in the list.")

# --- Example: Modifying the GET /status endpoint ---
@app.get("/status") # Define a Pydantic schema for the response if needed
def get_system_status(db: Session = Depends(get_db)):
    # Query the database for the latest 8 temperature readings
    latest_temps = db.query(models.TemperatureReadingDB)\
                     .order_by(models.TemperatureReadingDB.timestamp.desc())\
                     .limit(8)\
                     .all()

    # Query the latest solar data (assuming you created models.SolarPVDataDB)
    latest_solar = db.query(models.SolarPVDataDB)\
                     .order_by(models.SolarPVDataDB.timestamp.desc())\
                     .first() # Gets only the single latest record or None

    # You would need to query Fan/Peltier states too if you store them in DB
    # For now, returning placeholders or empty dicts if not stored in DB yet
    return {
        "temperatures": latest_temps,
        "fan_states": {}, # Replace with DB data if applicable
        "peltier_blocks": {}, # Replace with DB data if applicable
        "pump_states": {}, # Replace with DB data if applicable
        "hot_fan_pid_outputs": {}, # Replace with DB data if applicable
        "solar_data": latest_solar # Returns the object or None
    }

# --- Remember to update your other endpoints similarly ---
# (e.g., /solar_pv, /fan_control, /peltier_control)
# You'll need to define SQLAlchemy models for Fan, Peltier states if you
# want to store those in the database too.