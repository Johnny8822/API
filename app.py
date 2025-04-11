# app.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional # Ensure Optional is imported

# Import your modules (adjust paths if needed)
import models
import schemas
from database import engine, get_db

# --- This creates tables if they don't exist, including the new solar_pv_data ---
models.Base.metadata.create_all(bind=engine)
# -------------------------------------------------------------------------------

app = FastAPI()

# --- Temperature Endpoint (as modified before) ---
@app.post("/temperature", status_code=status.HTTP_201_CREATED)
async def receive_temperature(
    data: List[schemas.TemperatureReadingCreate],
    db: Session = Depends(get_db)
):
    created_count = 0
    for reading_data in data:
        db_reading = models.TemperatureReadingDB(
           sensor_id=reading_data.sensor_id,
           sensor_name=reading_data.sensor_name or f"Sensor_{reading_data.sensor_id}",
           temperature=reading_data.temperature,
           sensor_type=reading_data.sensor_type,
           battery_level=reading_data.battery_level
        )
        db.add(db_reading)
        created_count += 1

    if created_count > 0:
        try:
            db.commit()
            return {"message": f"{created_count} temperature reading(s) saved successfully."}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
    else:
         raise HTTPException(status_code=400, detail="No temperature readings provided in the list.")

# --- ADD POST /solar_pv ENDPOINT ---
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED)
async def receive_solar_data(
    data: schemas.SolarPVDataCreate, # Expect a single SolarPVDataCreate object
    db: Session = Depends(get_db)
):
    # Create the SQLAlchemy model instance
    db_solar_data = models.SolarPVDataDB(**data.model_dump()) # Convenient way to map fields

    db.add(db_solar_data)
    try:
        db.commit()
        db.refresh(db_solar_data) # Get ID and timestamp from DB
        return db_solar_data # Return the created record
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
# ----------------------------------

# --- ADD GET /status ENDPOINT ---
@app.get("/status", response_model=schemas.SystemStatus)
def get_system_status(db: Session = Depends(get_db)):
    # Query the database for the latest 8 temperature readings
    latest_temps = db.query(models.TemperatureReadingDB)\
                     .order_by(models.TemperatureReadingDB.timestamp.desc())\
                     .limit(8)\
                     .all()

    # Query the latest solar data
    latest_solar = db.query(models.SolarPVDataDB)\
                     .order_by(models.SolarPVDataDB.timestamp.desc())\
                     .first() # Gets only the single latest record or None

    # TODO: Query Fan/Peltier states if you add models/tables for them
    # For now, returning empty dicts as placeholders
    fan_states_from_db = {}
    peltier_blocks_from_db = {}
    pump_states_from_db = {} # Assuming pumps tied to peltier blocks might not need separate DB table
    hot_fan_pid_outputs_from_db = {} # Likely calculated, not stored?

    status_data = schemas.SystemStatus(
        temperatures=latest_temps,
        solar_data=latest_solar,
        fan_states=fan_states_from_db,
        peltier_blocks=peltier_blocks_from_db,
        pump_states=pump_states_from_db,
        hot_fan_pid_outputs=hot_fan_pid_outputs_from_db
    )

    return status_data
# -----------------------------

# --- Remember to add endpoints for FanControl and PeltierControl if needed ---
# Example:
# @app.put("/fan_control", response_model=schemas.FanControl)
# async def update_fan_speed(control: schemas.FanControl, db: Session = Depends(get_db)):
#     # Find fan state in DB (requires a FanState model/table)
#     # Update it
#     # Commit
#     # Return updated state
#     pass # Replace with actual implementation