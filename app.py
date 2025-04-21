# app.py
import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import models
import schemas
from database import engine, get_db

# --- Static Directory Configuration ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# --- Create Database Tables ---
print("Attempting to create database tables...")
try:
    models.Base.metadata.create_all(bind=engine)
    print("Database tables checked/created.")
except Exception as e:
    print(f"Error creating database tables: {e}")

app = FastAPI(title="Capstone API")

# --- CORS Configuration ---
origins = [
    "http://192.168.100.246:8000",
    "http://localhost",
    "http://localhost:8080",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoint to receive Temperature Data ---
@app.post("/temperature", status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_temperature(
    data: List[schemas.TemperatureReadingCreate], # Expect a LIST of creation objects
    db: Session = Depends(get_db)
):
    """
    Receives a list of temperature readings and saves them to the database.
    """
    created_count = 0
    # Loop through each reading sent in the list
    for reading_data in data:
        # Create the DB model instance
        db_reading = models.TemperatureReadingDB(
           sensor_id=reading_data.sensor_id,
           # Use the sensor_name if provided, otherwise default
           sensor_name=reading_data.sensor_name or f"Sensor_{reading_data.sensor_id}",
           temperature=reading_data.temperature,
           sensor_type=reading_data.sensor_type,
           battery_level=reading_data.battery_level
           # Timestamp uses default from model
        )
        db.add(db_reading)
        created_count += 1

    # Commit all readings added in the loop at once
    if created_count > 0:
        try:
            db.commit()
            print(f"Successfully saved {created_count} temperature readings.")
            return {"message": f"{created_count} temperature reading(s) saved successfully."}
        except Exception as e:
            db.rollback() # Rollback on error
            print(f"Error saving temperature readings: {e}")
            raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
    else:
         # If the input list was empty
         raise HTTPException(status_code=400, detail="No temperature readings provided in the list.")

# --- Endpoint to receive Solar PV Data ---
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_solar_data(
    data: schemas.SolarPVDataCreate, # Expect a single SolarPVDataCreate object
    db: Session = Depends(get_db)
):
    """
    Receives a single solar PV data reading and saves it to the database.
    """
    # Create the SQLAlchemy model instance using Pydantic's model_dump
    db_solar_data = models.SolarPVDataDB(**data.model_dump())

    db.add(db_solar_data)
    try:
        db.commit()
        db.refresh(db_solar_data) # Get ID and timestamp from DB
        print(f"Successfully saved solar PV data with ID: {db_solar_data.id}")
        return db_solar_data # Return the created record
    except Exception as e:
        db.rollback()
        print(f"Error saving solar PV data: {e}")
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")

# --- Endpoint to GET System Settings ---
@app.get("/settings", response_model=schemas.Settings, tags=["Settings"])
def get_settings(db: Session = Depends(get_db)):
    """
    Retrieves the current system settings (Setpoint, Timers, Fan Speeds).
    Creates default settings if none exist.
    """
    settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    if not settings:
        # If no settings row exists, create one with defaults from the model
        print("No settings found, creating default settings row...")
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            db.commit()
            db.refresh(settings)
            print("Default settings created.")
        except Exception as e:
            db.rollback()
            print(f"Error creating default settings: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create default settings: {e}")

    if not settings: # Should not happen after creation attempt, but safety check
         raise HTTPException(status_code=404, detail="Settings not found and could not be created")

    return settings

# --- Endpoint to PATCH System Settings ---
@app.patch("/settings", response_model=schemas.Settings, tags=["Settings"])
def update_settings(
    settings_update: schemas.SettingsUpdate, # Use the update schema (all fields optional)
    db: Session = Depends(get_db)
):
    """
    Updates specific system settings based on the provided fields.
    Only updates fields included in the request body.
    """
    settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    if not settings:
         # Attempt to create default settings if they don't exist before patching
         print("Settings not found during PATCH, attempting to create defaults...")
         settings = models.SystemSettings(id=1)
         db.add(settings)
         try:
             db.commit()
             db.refresh(settings)
             print("Default settings created during PATCH.")
         except Exception as e:
            db.rollback()
            print(f"Error creating default settings during PATCH: {e}")
            raise HTTPException(status_code=500, detail=f"Settings not found and could not be created: {e}")

    if not settings: # Check again after potential creation
        raise HTTPException(status_code=404, detail="Settings not found")

    # Get updated data as dict, excluding fields that were not sent in the request
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No settings provided for update")

    updated_fields_count = 0
    # Update the fields in the database model
    for key, value in update_data.items():
        if hasattr(settings, key):
             setattr(settings, key, value)
             updated_fields_count += 1
        else:
            print(f"Warning: Attempted to update non-existent setting field '{key}'")


    if updated_fields_count > 0:
        # Set updated_at manually to ensure it updates even if only one field changes
        # Note: onupdate in the model might handle this depending on backend/version
        settings.updated_at = datetime.now(pytz.timezone('America/Jamaica'))

        try:
            db.commit()
            db.refresh(settings)
            print(f"Successfully updated settings: {list(update_data.keys())}") # Log updated keys
            return settings
        except Exception as e:
            db.rollback()
            print(f"Error committing updated settings: {e}")
            raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
    else:
        # No valid fields were provided to update
        print("PATCH request received, but no valid fields found to update.")
        # Return current settings without making changes, or raise 400
        return settings


# --- Endpoint to GET System Status ---
@app.get("/status", response_model=schemas.SystemStatus, tags=["Status"])
def get_system_status(db: Session = Depends(get_db)):
    """
    Retrieves the latest sensor readings and current system settings.
    """
    # Query latest temps and solar
    latest_temps = db.query(models.TemperatureReadingDB)\
                     .order_by(models.TemperatureReadingDB.timestamp.desc())\
                     .limit(8)\
                     .all()
    latest_solar = db.query(models.SolarPVDataDB)\
                     .order_by(models.SolarPVDataDB.timestamp.desc())\
                     .first()

    # Query current settings (use the same logic as GET /settings)
    current_settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    if not current_settings:
       # Consistency: if GET /settings creates defaults, this should find them.
       # If it can still be None, handle appropriately based on SystemStatus schema
       print("Warning: Settings not found for status endpoint.")
       # Try creating default if missing
       current_settings = models.SystemSettings(id=1)
       db.add(current_settings)
       try:
           db.commit()
           db.refresh(current_settings)
       except Exception:
           db.rollback()
           current_settings = None # Fallback if creation fails here

    status_data = schemas.SystemStatus(
        temperatures=latest_temps,
        solar_data=latest_solar,
        current_settings=current_settings # Pass the settings object (or None)
    )
    return status_data


# --- HTML Page Endpoints ---
# --- Update HTML Endpoints ---
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Add explicit route for /temperatures
@app.get("/temperatures", response_class=FileResponse, include_in_schema=False)
async def read_temperatures():
    return FileResponse(os.path.join(STATIC_DIR, "temperatures.html"))

# Add explicit route for /settings
@app.get("/settings", response_class=FileResponse, include_in_schema=False)
async def read_settings():
    return FileResponse(os.path.join(STATIC_DIR, "settings.html"))

# Add explicit route for /pv_info
@app.get("/pv_info", response_class=FileResponse, include_in_schema=False)
async def read_pv_info():
    return FileResponse(os.path.join(STATIC_DIR, "pv_info.html"))



# --- MOUNT STATIC DIRECTORY (mount last, generally) ---
# This makes files like style.css and script.js accessible via /static/filename.ext
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# ------------------------------------------------------

# --- TODO: Add endpoints for FanControl and PeltierControl if needed ---
# These would likely interact with the SystemSettings table via PATCH /settings
# (e.g., updating fan_1_speed_percent) or potentially have their own endpoints
# if more complex logic (like PID control based on temperature) is needed.