# app.py
import logging
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
# Import AsyncSession from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, time
import pytz
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

# Import async_get_db and async_create_tables
from database import engine, get_db as async_get_db, create_tables as async_create_tables # Alias get_db for clarity
import models # Models are unchanged
import schemas # Schemas are unchanged

# Import select for constructing async queries
from sqlalchemy import select, update, insert, delete # Import select for async queries
from sqlalchemy import asc # Import asc for ascending order


# --- Static Directory Configuration ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Capstone API")

# --- Create Database Tables on Startup ---\
# Use the FastAPI startup event to run the async creation
@app.on_event("startup")
async def startup_event():
    await async_create_tables() # Call the async create function

# --- CORS Configuration ---
origins = [
    "http://192.168.100.246:8000",
    "http://localhost",
    "http://localhost:8080",
    # Add other origins if needed, but avoid "*" in production if possible
    # Example: Add your VM's specific IP if accessing from another machine
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoint to receive Temperature Readings from ESP32 (Example) ---
# ASSUME this endpoint is updated to receive and save status fields
# from the ESP32 into the SystemSettings table.
# This is a placeholder and needs to be implemented based on your ESP32 communication.
@app.post("/temperature", response_model=schemas.TemperatureReading, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_temperature(reading: schemas.TemperatureReadingCreate, db: AsyncSession = Depends(async_get_db)):
    """
    Receives a new temperature reading from an ESP32.
    ENSURE this endpoint also receives and SAVES the latest component statuses
    into the SystemSettings table (id=1).
    """
    # Convert schema object to model object
    db_reading = models.TemperatureReadingDB(**reading.model_dump())

    # Example: You would need logic here to receive status data from the ESP32
    # alongside the temperature reading and update the SystemSettings row:
    # status_data_from_esp32 = ... # Parse status from incoming request
    # settings_row = await db.get(models.SystemSettings, 1)
    # if settings_row:
    #    settings_row.fan_1_status = status_data_from_esp32.fan_1
    #    # ... update other status fields ...
    #    db.add(settings_row) # Add changes to session

    db.add(db_reading)
    await db.commit()
    await db.refresh(db_reading)
    print(f"Received and saved temperature reading: Sensor ID {db_reading.sensor_id}, Temp {db_reading.temperature}")
    return db_reading

# --- Endpoint to receive Solar PV Data from ESP32 (Example) ---
# ASSUME this endpoint is updated to receive and save status fields if status is sent here
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_solar_pv(data: schemas.SolarPVDataCreate, db: AsyncSession = Depends(async_get_db)):
    """
    Receives new solar PV data from an ESP32.
    ENSURE this endpoint also receives and SAVES the latest component statuses
    into the SystemSettings table (id=1) if status is sent with PV data.
    """
    # Convert schema object to model object
    db_data = models.SolarPVDataDB(**data.model_dump())
     # Example: If status comes with PV data, update SystemSettings row here too
     # settings_row = await db.get(models.SystemSettings, 1)
     # if settings_row:
     #    settings_row.pump_1_status = status_data_from_esp32.pump_1
     #    # ... update other status fields ...
     #    db.add(settings_row) # Add changes to session

    db.add(db_data)
    await db.commit()
    await db.refresh(db_data)
    print(f"Received and saved solar PV data: Batt V {db_data.battery_voltage}, Load W {db_data.load_power}")
    return db_data


# --- Endpoint to GET System Settings (Editable Parameters + Status) ---
# This endpoint fetches editable settings + status from the DB
@app.get("/api/settings", response_model=schemas.Settings, tags=["Settings"]) # Use /api/settings
async def get_settings(db: AsyncSession = Depends(async_get_db)):
    """
    Retrieves the current system settings (Setpoint, Timers, Fan Speeds, Status).
    Creates default settings if none exist.
    """
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt)

    if not settings:
        print("No settings found, creating default settings row...")
        # Default status fields will be False/None initially
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            await db.commit()
            await db.refresh(settings)
            print("Default settings created and committed.")
            return settings # Return the newly created settings
        except Exception as e:
            await db.rollback()
            print(f"Error creating default settings: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create default settings: {e}")

    return settings # Return the settings object


# --- Endpoint to PATCH System Settings (Editable Parameters Only) ---
@app.patch("/api/settings", response_model=schemas.Settings, tags=["Settings"]) # Use /api/settings
async def update_settings(
    settings_update: schemas.SettingsUpdate, # Only includes editable fields (Setpoint, Timers, Fan 4 & 2 Speed)
    db: AsyncSession = Depends(async_get_db)
):
    """
    Updates specific system settings (Setpoint, Timers, Controllable Fan Speeds)
    based on the provided fields. Only updates fields included in the request body.
    Status fields and non-controllable speeds are ignored if sent.
    """
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt)

    if not settings:
        # Attempt to create default settings if they don't exist before patching
        print("Settings not found during PATCH, attempting to create defaults...")
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            await db.commit()
            await db.refresh(settings)
            print("Default settings created during PATCH.")
        except Exception as e:
            await db.rollback()
            print(f"Error creating default settings during PATCH: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Settings not found and could not be created: {e}")


    # Get the fields to update from the request body, excluding fields that were not set
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        print("PATCH request received, but no valid fields found to update.")
        # Refresh settings to get latest status before returning if needed, though client will fetch status separately
        # await db.refresh(settings) # Refreshing here might be good to return latest status
        return settings # Return existing settings (with potentially stale status)

    # Update the fields in the database model object
    updated_fields_count = 0
    for key, value in update_data.items():
        # Check if the key is a valid, *editable* field in the SystemSettings model
        # The fields in SettingsUpdate should match the editable fields in SystemSettings model
        if hasattr(models.SystemSettings, key): # Simple check
             # Ensure we don't accidentally update status fields if they were somehow sent
             # (The SettingsUpdate schema should prevent this, but this adds a layer)
             if key in schemas.SettingsUpdate.model_fields: # Check if the field is in the SettingsUpdate schema
                setattr(settings, key, value)
                updated_fields_count += 1
                print(f"Updating setting: {key} = {value}")
             else:
                 print(f"Warning: Attempted to update non-editable field '{key}' via PATCH.")
        else:
            print(f"Warning: Attempted to update non-existent setting field '{key}'")


    # The onupdate in the model should handle updated_at, but ensure it works.
    # settings.updated_at = datetime.now(pytz.timezone('America/Jamaica')) # Can remove manual update if onupdate works

    try:
        await db.commit()
        await db.refresh(settings) # Refresh to get the potentially updated 'updated_at' and any system-set status
        print(f"Successfully updated {updated_fields_count} settings.")
        return settings
    except Exception as e:
        await db.rollback()
        print(f"Error committing updated settings: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Status ---
# This endpoint fetches the latest sensor readings AND the current SystemSettings (including status and all speeds)
@app.get("/status", response_model=schemas.SystemStatus, tags=["Status"])
async def get_system_status(db: AsyncSession = Depends(async_get_db)):
    """
    Retrieves the latest sensor readings and current system settings (including status).
    """
    # Query latest temps and solar using async queries (no changes needed here)
    temp_stmt = select(models.TemperatureReadingDB)\
                 .order_by(models.TemperatureReadingDB.timestamp.desc())\
                 .limit(8)
    latest_temps = await db.scalars(temp_stmt).all()

    solar_stmt = select(models.SolarPVDataDB)\
                  .order_by(models.SolarPVDataDB.timestamp.desc())\
                  .limit(1)
    latest_solar = await db.scalar(solar_stmt)

    # Query current settings (including all speeds and status) from the SystemSettings table
    settings_stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    current_settings = await db.scalar(settings_stmt)

    # If settings don't exist, attempt to create default (this will also create status/speeds fields with defaults)
    if not current_settings:
        print("Warning: Settings not found for status endpoint, attempting to create defaults.")
        try:
            # Default status fields will be False/None, default speeds 50%
            settings = models.SystemSettings(id=1)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
            current_settings = settings
            print("Default settings created for status endpoint.")
        except Exception as e:
             await db.rollback()
             print(f"Error creating default settings for status endpoint: {e}")
             current_settings = None # Ensure it's None if creation fails, so response reflects missing settings

    # Construct the SystemStatus response model - it will now include all speeds and status from current_settings
    status_data = schemas.SystemStatus(
        temperatures=latest_temps,
        solar_data=latest_solar,
        current_settings=current_settings # This object now contains all speed and status fields
    )
    return status_data


# --- New Endpoint to GET Temperature History Data ---
# Assumes you want this under the /api prefix for consistency
@app.get("/api/temperature_history", response_model=List[schemas.TemperatureReading], tags=["Sensor Data"])
async def get_temperature_history(
    sensor_name: Optional[str] = Query(None, description="Filter by sensor name"),
    limit: int = Query(100, description="Limit the number of readings"), # Default limit to 100
    start_time: Optional[datetime] = Query(None, description="Filter by start time (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time (ISO 8601)"),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Retrieves historical temperature readings, optionally filtered by sensor name and time range.
    Returns the latest readings within the filter.
    """
    logging.info(f"Fetching temperature history: sensor_name={sensor_name}, limit={limit}, start_time={start_time}, end_time={end_time}")

    stmt = select(models.TemperatureReadingDB)

    if sensor_name:
        stmt = stmt.where(models.TemperatureReadingDB.sensor_name == sensor_name)

    if start_time:
        # Ensure timezone awareness if needed, assuming DB stores timezone-aware datetimes
        # Pydantic should handle parsing ISO 8601 string with timezone info
        stmt = stmt.where(models.TemperatureReadingDB.timestamp >= start_time)

    if end_time:
        # Ensure timezone awareness if needed
        stmt = stmt.where(models.TemperatureReadingDB.timestamp <= end_time)

    # Order ascending by timestamp for graphs
    stmt = stmt.order_by(models.TemperatureReadingDB.timestamp.asc()).limit(limit)


    try:
        readings = await db.scalars(stmt).all()
        logging.info(f"Fetched {len(readings)} temperature history readings.")
        # Returning a List[schemas.TemperatureReading] will automatically serialize ORM objects
        return readings
    except Exception as e:
        logging.error(f"Error fetching temperature history: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error fetching history: {e}")


# --- HTML Page Endpoints ---
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    file_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(file_path)

# Redirect /index to /
@app.get("/index", include_in_schema=False)
async def redirect_index():
    return RedirectResponse(url="/")

@app.get("/temperatures", response_class=FileResponse, include_in_schema=False)
async def read_temperatures():
    file_path = os.path.join(STATIC_DIR, "temperatures.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="temperatures.html not found")
    return FileResponse(file_path)

@app.get("/settings", response_class=FileResponse, include_in_schema=False)
async def read_settings():
    file_path = os.path.join(STATIC_DIR, "settings.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="settings.html not found")
    return FileResponse(file_path)

@app.get("/pv_info", response_class=FileResponse, include_in_schema=False)
async def read_pv_info():
    file_path = os.path.join(STATIC_DIR, "pv_info.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="pv_info.html not found")
    return FileResponse(file_path)

# New HTML Page Endpoint for Temperature Graphs
@app.get("/temperature_graphs", response_class=FileResponse, include_in_schema=False)
async def read_temperature_graphs():
    file_path = os.path.join(STATIC_DIR, "temperature_graphs.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="temperature_graphs.html not found")
    return FileResponse(file_path)


# --- MOUNT STATIC DIRECTORY (mount last, generally) ---
# This makes files like style.css and script.js accessible via /static/filename.ext
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# ------------------------------------------------------

# --- TODO: Add endpoint to receive status data from ESP32 if not included in temp/pv endpoints ---
# This is crucial for status indicators to work.
# Example (assuming JSON body with status fields):
# @app.post("/status_update", status_code=status.HTTP_200_OK)
# async def receive_status_update(status_data: schemas.SystemStatusUpdateFromESP32, db: AsyncSession = Depends(async_get_db)):
#    settings_row = await db.get(models.SystemSettings, 1)
#    if settings_row:
#        update_data = status_data.model_dump(exclude_unset=True)
#        for key, value in update_data.items():
#            if hasattr(settings_row, key):
#                setattr(settings_row, key, value)
#        await db.commit()
#        # No refresh needed unless you need updated_at back
#        return {"message": "Status updated"}
#    raise HTTPException(status_code=404, detail="Settings row not found")