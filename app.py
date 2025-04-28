# app.py
import os
import logging # Import logging
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
# Assuming your database.py has the correct async setup now
from database import engine, get_db as async_get_db, create_tables as async_create_tables # Alias get_db for clarity
import models # Your models should be updated
import schemas # Your schemas should be updated

# Import select for constructing async queries
from sqlalchemy import select, update, insert, delete # Import select for async queries
from sqlalchemy import asc # Import asc for ascending order

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Static Directory Configuration ---
# Ensure this path is correct relative to where you run app.py
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
logger.info(f"Serving static files from: {STATIC_DIR}") # Log the static directory path


app = FastAPI(title="Capstone API")

# --- Create Database Tables on Startup ---
# Use the FastAPI startup event to run the async creation
@app.on_event("startup")
async def startup_event():
    logger.info("Running startup event: creating database tables...")
    await async_create_tables() # Call the async create function
    logger.info("Database tables creation finished.")

# --- CORS Configuration ---
origins = [
    "http://192.168.100.246:8000", # Your VM's IP and port
    "http://localhost",
    "http://localhost:8080", # Common for local development
    # Add other specific origins if needed
    "*" # WARNING: Using "*" is insecure in production. Be specific with origins.
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
    logger.info(f"Received temperature reading POST: {reading.model_dump()}")

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
    # Explicitly commit here as we are creating data
    try:
        await db.commit()
        await db.refresh(db_reading)
        logger.info(f"Successfully saved temperature reading with ID: {db_reading.id}")
        # Return the created record
        return db_reading
    except Exception as e:
        await db.rollback() # Rollback on error
        logger.error(f"Error saving temperature reading: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to receive Solar PV Data from ESP32 (Example) ---
# ASSUME this endpoint is updated to receive and save status fields if status is sent here
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_solar_data(data: schemas.SolarPVDataCreate, db: AsyncSession = Depends(async_get_db)):
    """
    Receives a single solar PV data reading and saves it to the database.
    ENSURE this endpoint also receives and SAVES the latest component statuses
    into the SystemSettings table (id=1) if status is sent with PV data.
    """
    logger.info(f"Received solar PV data POST: {data.model_dump()}")

    # Create the SQLAlchemy model instance using Pydantic's model_dump
    db_solar_data = models.SolarPVDataDB(**data.model_dump())

    db.add(db_solar_data) # db.add is synchronous on the session object
    # Commit handled by dependency, refresh needed if returning the object
    # try:
    #     await db.commit()
    #     await db.refresh(db_solar_data) # Get ID and timestamp from DB - this needs await!
    #     print(f"Successfully saved solar PV data with ID: {db_solar_data.id}")
    #     return db_solar_data # Return the created record
    # except Exception as e:
    #     await db.rollback()
    #     print(f"Error saving solar PV data: {e}")
    #     raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")

    # If using the commit within the dependency, you might need to refresh AFTER the commit
    # in the dependency's finally block if you want to return the object here with DB-generated fields.
    # Or, explicitly commit here. Let's explicitly commit for clarity in this endpoint.
    try:
        await db.commit()
        await db.refresh(db_solar_data) # Refresh after commit to get DB-generated ID/timestamp
        logger.info(f"Successfully saved solar PV data with ID: {db_solar_data.id}")
        return db_solar_data
    except Exception as e:
        await db.rollback()
        logger.error(f"Error saving solar PV data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Settings (Editable Parameters + Status) ---
# This endpoint fetches editable settings + status from the DB
@app.get("/api/settings", response_model=schemas.Settings, tags=["Settings"]) # Use /api/settings
async def get_settings(db: AsyncSession = Depends(async_get_db)):
    """
    Retrieves the current system settings (Setpoint, Timers, Fan Speeds, Status).
    Creates default settings if none exist.
    """
    logger.info("Entering get_settings endpoint.")
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt) # Use await db.scalar

    if not settings:
        logger.warning("No settings found, creating default settings row...")
        # Default status fields will be False/None initially
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            await db.commit() # Explicitly commit creation
            await db.refresh(settings)
            logger.info("Default settings created and committed.")
            return settings # Return the newly created settings
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating default settings: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create default settings: {e}")

    logger.info("Successfully retrieved settings.")
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
    logger.info(f"Entering update_settings endpoint. Received update data: {settings_update.model_dump(exclude_unset=True)}")

    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt) # Use await db.scalar

    if not settings:
        # Attempt to create default settings if they don't exist before patching
        logger.warning("Settings not found during PATCH, attempting to create defaults...")
        settings = models.SystemSettings(id=1)
        db.add(settings)
        # Explicitly commit creation
        try:
            await db.commit()
            await db.refresh(settings)
            logger.info("Default settings created during PATCH.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating default settings during PATCH: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Settings not found and could not be created: {e}")


    if not settings: # Check again after potential creation
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")


    # Get the fields to update from the request body, excluding fields that were not set
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        # Return current settings if no update data provided (PATCH allows this)
        logger.info("PATCH request received, but no valid fields found to update.")
        # Refresh settings to return latest status etc.
        # await db.refresh(settings) # Refreshing here might be good to return latest status
        return settings # Return existing settings


    updated_fields_count = 0
    # Update the fields in the database model object
    for key, value in update_data.items():
        # Check if the key is a valid, *editable* field in the SystemSettings model
        # The fields in SettingsUpdate should match the editable fields in SystemSettings model
        # Added an extra check to ensure the key is defined in the SettingsUpdate schema
        if hasattr(models.SystemSettings, key) and key in schemas.SettingsUpdate.model_fields:
            setattr(settings, key, value)
            updated_fields_count += 1
            logger.info(f"Updating setting: {key} = {value}")
        else:
            logger.warning(f"Attempted to update non-editable or non-existent setting field '{key}' via PATCH.")


    # The onupdate in the model should handle updated_at, but ensure it works.
    # settings.updated_at = datetime.now(pytz.timezone('America/Jamaica')) # Can remove manual update if onupdate works

    # Commit the changes. Explicitly commit for updates.
    try:
        await db.commit()
        await db.refresh(settings) # Refresh to get the potentially updated 'updated_at' and any system-set status
        logger.info(f"Successfully updated {updated_fields_count} settings.")
        return settings
    except Exception as e:
        await db.rollback()
        logger.error(f"Error committing updated settings: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Status ---
# This endpoint fetches the latest sensor readings AND the current SystemSettings (including status and all speeds)
@app.get("/status", response_model=schemas.SystemStatus, tags=["Status"])
async def get_system_status(db: AsyncSession = Depends(async_get_db)): # Use AsyncSession and async_get_db
    """
    Retrieves the latest sensor readings and current system settings (including status).
    """
    logger.info("Entering get_system_status endpoint. Fetching latest data...")

    # Query latest temps using async queries
    temp_stmt = select(models.TemperatureReadingDB)\
                 .order_by(models.TemperatureReadingDB.timestamp.desc())\
                 .limit(8)
    # CORRECTED SYNTAX: Split await and .all()
    try:
        scalars_result = await db.scalars(temp_stmt) # Await the coroutine
        latest_temps = scalars_result.all() # Call .all() on the awaited result
        logger.info(f"Fetched {len(latest_temps)} latest temperature readings.")
    except Exception as e:
         logger.error(f"Error fetching latest temperatures: {e}", exc_info=True)
         latest_temps = [] # Return empty list on error or raise exception


    # Query latest solar using async query
    solar_stmt = select(models.SolarPVDataDB)\
                  .order_by(models.SolarPVDataDB.timestamp.desc())\
                  .limit(1) # Limit 1 for .first()
    # CORRECTED SYNTAX: await db.scalar(stmt) - this syntax is fine for single result
    try:
        latest_solar = await db.scalar(solar_stmt) # Use await db.scalar(...) for first
        if latest_solar:
             logger.info("Fetched latest solar PV data.")
        else:
             logger.info("No solar PV data found.")
    except Exception as e:
         logger.error(f"Error fetching latest solar data: {e}", exc_info=True)
         latest_solar = None # Return None on error or raise exception


    # Query current settings (including all speeds and status) from the SystemSettings table
    settings_stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    # CORRECTED SYNTAX: await db.scalar(stmt) - this syntax is fine for single result
    try:
        current_settings = await db.scalar(settings_stmt) # Use await db.scalar
        if current_settings:
             logger.info("Fetched current system settings.")
        else:
             logger.warning("No system settings found.")
    except Exception as e:
        logger.error(f"Error fetching current settings: {e}", exc_info=True)
        current_settings = None # Return None on error or raise exception


    # If settings don't exist, attempt to create default (consistency with /settings endpoint)
    # This logic might be better handled within the /api/settings GET endpoint on its first call
    # and relying on that row existing for subsequent status calls.
    # If you keep this creation logic here, ensure it handles potential race conditions
    # if multiple status requests come before settings is first saved.
    # For now, we'll rely on the /api/settings GET/PATCH to ensure the row exists.
    # If current_settings is None here, the response model will handle the Optional[Settings]


    # Construct the SystemStatus response model - it will now include all speeds and status from current_settings
    status_data = schemas.SystemStatus(
        temperatures=latest_temps, # These are SQLAlchemy ORM objects, Pydantic with from_attributes=True handles conversion
        solar_data=latest_solar,   # SQLAlchemy ORM object (or None)
        current_settings=current_settings # SQLAlchemy ORM object (or None)
    )
    logger.info("Successfully constructed system status response.")
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
    logger.info(f"Entering get_temperature_history: sensor_name={sensor_name}, limit={limit}, start_time={start_time}, end_time={end_time}")

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
        # CORRECTED SYNTAX: Split await and .all()
        scalars_result = await db.scalars(stmt) # Await the coroutine
        readings = scalars_result.all() # Call .all() on the awaited result
        logger.info(f"Fetched {len(readings)} temperature history readings.")
        # Returning a List[schemas.TemperatureReading] will automatically serialize ORM objects
        return readings
    except Exception as e:
        logger.error(f"Error fetching temperature history: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error fetching history: {e}")


# --- HTML Page Endpoints ---
# These typically don't interact with the DB, so no async DB changes needed here.
# Ensure your static files are accessible.
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    # Use async os operations if reading large files, but FileResponse handles this generally
    file_path = os.path.join(STATIC_DIR, "index.html")
    logger.info(f"Serving index.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"index.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="index.html not found")
    return FileResponse(file_path)

# Redirect /index to /
@app.get("/index", include_in_schema=False)
async def redirect_index():
    logger.info("Redirecting /index to /")
    return RedirectResponse(url="/")

# Add explicit route for /temperatures
@app.get("/temperatures", response_class=FileResponse, include_in_schema=False)
async def read_temperatures():
    file_path = os.path.join(STATIC_DIR, "temperatures.html")
    logger.info(f"Serving temperatures.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"temperatures.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="temperatures.html not found")
    return FileResponse(file_path)

@app.get("/settings", response_class=FileResponse, include_in_schema=False)
async def read_settings():
    file_path = os.path.join(STATIC_DIR, "settings.html")
    logger.info(f"Serving settings.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"settings.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="settings.html not found")
    return FileResponse(file_path)

# Add explicit route for /pv_info
@app.get("/pv_info", response_class=FileResponse, include_in_schema=False)
async def read_pv_info():
    file_path = os.path.join(STATIC_DIR, "pv_info.html")
    logger.info(f"Serving pv_info.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"pv_info.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pv_info.html not found")
    return FileResponse(file_path)

# New HTML Page Endpoint for Temperature Graphs
@app.get("/temperature_graphs", response_class=FileResponse, include_in_schema=False)
async def read_temperature_graphs():
    file_path = os.path.join(STATIC_DIR, "temperature_graphs.html")
    logger.info(f"Serving temperature_graphs.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"temperature_graphs.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="temperature_graphs.html not found")
    return FileResponse(file_path)


# --- MOUNT STATIC DIRECTORY (mount last, generally) ---
# This makes files like style.css and script.js accessible via /static/filename.ext
# Ensure the directory exists and contains the static files
if not os.path.exists(STATIC_DIR):
    logger.error(f"Static directory NOT FOUND at: {STATIC_DIR}")
    # You might want to raise an error or handle this case
else:
    logger.info(f"Mounting static directory at: {STATIC_DIR}")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# ------------------------------------------------------

# --- TODO: Add endpoint to receive status data from ESP32 if not included in temp/pv endpoints ---
# This is crucial for status indicators to work.
# Example (assuming JSON body with status fields, and schema SystemStatusUpdateFromESP32):
# @app.post("/status_update", status_code=status.HTTP_200_OK)
# async def receive_status_update(status_data: schemas.SystemStatusUpdateFromESP32, db: AsyncSession = Depends(async_get_db)):
#    logger.info(f"Received status update: {status_data.model_dump()}")
#    settings_row = await db.get(models.SystemSettings, 1)
#    if settings_row:
#        update_data = status_data.model_dump(exclude_unset=True)
#        for key, value in update_data.items():
#            if hasattr(settings_row, key):
#                setattr(settings_row, key, value)
#        await db.commit()
#        # No refresh needed unless you need updated_at back
#        return {"message": "Status updated successfully"}
#    logger.error("Settings row not found for status update.")
#    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings row not found")