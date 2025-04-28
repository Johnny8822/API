# app.py
import os
import logging
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
import models
import schemas

# Import select for constructing async queries
from sqlalchemy import select, update, insert, delete
from sqlalchemy import asc # Import asc for ascending order

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Static Directory Configuration ---
# Ensure this path is correct relative to where you run app.py
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
logger.info(f"Serving static files from: {STATIC_DIR}")


app = FastAPI(title="Capstone API")

# --- Create Database Tables on Startup ---
# Use the FastAPI startup event to run the async creation
@app.on_event("startup")
async def startup_event():
    logger.info("Running startup event: creating database tables...")
    await async_create_tables()
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


# --- Endpoint to receive Temperature Readings from ESP32 ---
@app.post("/temperature", response_model=schemas.TemperatureReading, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_temperature(reading: schemas.TemperatureReadingCreate, db: AsyncSession = Depends(async_get_db)): # Expect a SINGLE creation object
    """
    Receives a new temperature reading from an ESP32.
    """
    logger.info(f"Received temperature reading POST: {reading.model_dump()}")

    # Convert schema object to model object
    db_reading = models.TemperatureReadingDB(**reading.model_dump())

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

# --- Endpoint to receive a LIST of Temperature Readings from ESP32 ---
# This endpoint expects the list format that your ESP32 is currently sending
@app.post("/temperature/bulk", status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_temperature_bulk(
    data: List[schemas.TemperatureReadingCreate], # Expect a LIST of creation objects
    db: AsyncSession = Depends(async_get_db) # Use AsyncSession and async_get_db
):
    """
    Receives a list of temperature readings and saves them to the database.
    """
    logger.info(f"Received bulk temperature readings POST: {len(data)} readings.")

    if not data: # Check if list is empty
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No temperature readings provided in the list.")

    db_readings = []
    # Loop through each reading sent in the list
    for reading_data in data:
        # Create the DB model instance
        db_reading = models.TemperatureReadingDB(
            sensor_id=reading_data.sensor_id,
            sensor_name=reading_data.sensor_name or f"Sensor_{reading_data.sensor_id}",
            temperature=reading_data.temperature,
            sensor_type=reading_data.sensor_type,
            battery_level=reading_data.battery_level
            # Timestamp uses default from model
        )
        db_readings.append(db_reading)

    # Add all readings at once (often more efficient)
    db.add_all(db_readings)

    # Explicitly commit here for bulk insert
    try:
        await db.commit()
        # Refresh is often not needed for bulk insert unless you need IDs back immediately
        # await db.refresh(...) # Refreshing a list of objects can be inefficient
        logger.info(f"Successfully saved {len(db_readings)} temperature readings.")
        return {"message": f"Successfully saved {len(db_readings)} temperature readings."}
    except Exception as e:
        await db.rollback() # Rollback on error
        logger.error(f"Error saving bulk temperature readings: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to receive Solar PV Data from ESP32 (Example) ---
# ASSUME this endpoint is updated to receive and save status fields if status is sent here
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_solar_data(data: schemas.SolarPVDataCreate, db: AsyncSession = Depends(async_get_db)):
    """
    Receives a single solar PV data reading and saves it to the database.
    """
    logger.info(f"Received solar PV data POST: {data.model_dump()}")

    # Create the SQLAlchemy model instance using Pydantic's model_dump
    db_solar_data = models.SolarPVDataDB(**data.model_dump())

    db.add(db_solar_data)
    # Explicitly commit here
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
@app.get("/api/settings", response_model=schemas.Settings, tags=["Settings"])
async def get_settings(db: AsyncSession = Depends(async_get_db)):
    """
    Retrieves the current system settings (Setpoint, Timers, Fan Speeds, Status).
    Creates default settings if none exist.
    """
    logger.info("Entering get_settings endpoint.")
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt)

    if not settings:
        logger.warning("No settings found, creating default settings row...")
        settings = models.SystemSettings(id=1) # Default status fields will be False/None initially
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
    return settings


# --- Endpoint to PATCH System Settings (Editable Parameters Only) ---
@app.patch("/api/settings", response_model=schemas.Settings, tags=["Settings"])
async def update_settings(
    settings_update: schemas.SettingsUpdate,
    db: AsyncSession = Depends(async_get_db)
):
    """
    Updates specific system settings (Setpoint, Timers, Controllable Fan Speeds)
    based on the provided fields. Only updates fields included in the request body.
    Status fields and non-controllable speeds are ignored if sent.
    """
    logger.info(f"Entering update_settings endpoint. Received update data: {settings_update.model_dump(exclude_unset=True)}")

    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt)

    if not settings:
        logger.warning("Settings not found during PATCH, attempting to create defaults...")
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            await db.commit()
            await db.refresh(settings)
            logger.info("Default settings created during PATCH.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating default settings during PATCH: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Settings not found and could not be created: {e}")


    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")


    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        logger.info("PATCH request received, but no valid fields found to update.")
        return settings


    updated_fields_count = 0
    for key, value in update_data.items():
        if hasattr(models.SystemSettings, key) and key in schemas.SettingsUpdate.model_fields:
            setattr(settings, key, value)
            updated_fields_count += 1
            logger.info(f"Updating setting: {key} = {value}")
        else:
            logger.warning(f"Attempted to update non-editable or non-existent setting field '{key}' via PATCH.")


    try:
        await db.commit()
        await db.refresh(settings)
        logger.info(f"Successfully updated {updated_fields_count} settings.")
        return settings
    except Exception as e:
        await db.rollback()
        logger.error(f"Error committing updated settings: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Status ---
@app.get("/status", response_model=schemas.SystemStatus, tags=["Status"])
async def get_system_status(db: AsyncSession = Depends(async_get_db)):
    """
    Retrieves the latest sensor readings and current system settings (including status).
    """
    logger.info("Entering get_system_status endpoint. Fetching latest data...")

    temp_stmt = select(models.TemperatureReadingDB)\
                 .order_by(models.TemperatureReadingDB.timestamp.desc())\
                 .limit(8)
    try:
        scalars_result = await db.scalars(temp_stmt)
        latest_temps = scalars_result.all()
        logger.info(f"Fetched {len(latest_temps)} latest temperature readings.")
    except Exception as e:
         logger.error(f"Error fetching latest temperatures: {e}", exc_info=True)
         latest_temps = []


    solar_stmt = select(models.SolarPVDataDB)\
                  .order_by(models.SolarPVDataDB.timestamp.desc())\
                  .limit(1)
    try:
        latest_solar = await db.scalar(solar_stmt)
        if latest_solar:
             logger.info("Fetched latest solar PV data.")
        else:
             logger.info("No solar PV data found.")
    except Exception as e:
         logger.error(f"Error fetching latest solar data: {e}", exc_info=True)
         latest_solar = None


    settings_stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    try:
        current_settings = await db.scalar(settings_stmt)
        if current_settings:
             logger.info("Fetched current system settings.")
        else:
             logger.warning("No system settings found.")
    except Exception as e:
        logger.error(f"Error fetching current settings: {e}", exc_info=True)
        current_settings = None


    status_data = schemas.SystemStatus(
        temperatures=latest_temps,
        solar_data=latest_solar,
        current_settings=current_settings
    )
    logger.info("Successfully constructed system status response.")
    return status_data


# --- Endpoint to GET Temperature History Data ---
@app.get("/api/temperature_history", response_model=List[schemas.TemperatureReading], tags=["Sensor Data"])
async def get_temperature_history(
    sensor_name: Optional[str] = Query(None, description="Filter by sensor name"),
    limit: int = Query(100, description="Limit the number of readings"),
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
        stmt = stmt.where(models.TemperatureReadingDB.timestamp >= start_time)

    if end_time:
        stmt = stmt.where(models.TemperatureReadingDB.timestamp <= end_time)

    stmt = stmt.order_by(models.TemperatureReadingDB.timestamp.asc()).limit(limit)


    try:
        scalars_result = await db.scalars(stmt)
        readings = scalars_result.all()
        logger.info(f"Fetched {len(readings)} temperature history readings.")
        return readings
    except Exception as e:
        logger.error(f"Error fetching temperature history: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error fetching history: {e}")


# --- HTML Page Endpoints ---
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    file_path = os.path.join(STATIC_DIR, "index.html")
    logger.info(f"Serving index.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"index.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="index.html not found")
    return FileResponse(file_path)

@app.get("/index", include_in_schema=False)
async def redirect_index():
    logger.info("Redirecting /index to /")
    return RedirectResponse(url="/")

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

@app.get("/pv_info", response_class=FileResponse, include_in_schema=False)
async def read_pv_info():
    file_path = os.path.join(STATIC_DIR, "pv_info.html")
    logger.info(f"Serving pv_info.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"pv_info.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pv_info.html not found")
    return FileResponse(file_path)

@app.get("/temperature_graphs", response_class=FileResponse, include_in_schema=False)
async def read_temperature_graphs():
    file_path = os.path.join(STATIC_DIR, "temperature_graphs.html")
    logger.info(f"Serving temperature_graphs.html from: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"temperature_graphs.html not found at {file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="temperature_graphs.html not found")
    return FileResponse(file_path)


# --- MOUNT STATIC DIRECTORY (mount last, generally) ---
if not os.path.exists(STATIC_DIR):
    logger.error(f"Static directory NOT FOUND at: {STATIC_DIR}")
else:
    logger.info(f"Mounting static directory at: {STATIC_DIR}")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- TODO: Add endpoint to receive status data from ESP32 ---
# ... (Endpoint logic for receiving status updates) ...