# app.py
import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
# Import AsyncSession from sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
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


# --- Static Directory Configuration ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Capstone API")

# --- Create Database Tables on Startup ---
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
# Change the dependency to use async_get_db and AsyncSession
@app.post("/temperature", status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_temperature(
    data: List[schemas.TemperatureReadingCreate], # Expect a LIST of creation objects
    db: AsyncSession = Depends(async_get_db) # Use AsyncSession and async_get_db
):
    """
    Receives a list of temperature readings and saves them to the database.
    """
    if not data:
        raise HTTPException(status_code=400, detail="No temperature readings provided in the list.")

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
    db.add_all(db_readings) # db.add_all is synchronous on the session object

    # The commit is handled by the async_get_db dependency's finally block
    # But you could also commit explicitly here if you remove the commit from the dependency
    # try:
    #     await db.commit()
    #     print(f"Successfully saved {len(db_readings)} temperature readings.")
    #     # Refresh each object if needed to get generated IDs, etc.
    #     # for reading in db_readings:
    #     #     await db.refresh(reading)
    #     return {"message": f"{len(db_readings)} temperature reading(s) saved successfully."}
    # except Exception as e:
    #     await db.rollback() # Rollback on error
    #     print(f"Error saving temperature readings: {e}")
    #     raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")

    # If using the commit within the dependency:
    print(f"Successfully added {len(db_readings)} temperature readings to session.")
    return {"message": f"{len(db_readings)} temperature reading(s) added to session, committing via dependency."}


# --- Endpoint to receive Solar PV Data ---
# Change the dependency to use async_get_db and AsyncSession
@app.post("/solar_pv", response_model=schemas.SolarPVData, status_code=status.HTTP_201_CREATED, tags=["Sensor Data"])
async def receive_solar_data(
    data: schemas.SolarPVDataCreate, # Expect a single SolarPVDataCreate object
    db: AsyncSession = Depends(async_get_db) # Use AsyncSession and async_get_db
):
    """
    Receives a single solar PV data reading and saves it to the database.
    """
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
        print(f"Successfully saved solar PV data with ID: {db_solar_data.id}")
        return db_solar_data
    except Exception as e:
        await db.rollback()
        print(f"Error saving solar PV data: {e}")
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Settings ---
# Change the dependency to use async_get_db and AsyncSession
@app.get("/settings", response_model=schemas.Settings, tags=["Settings"])
async def get_settings(db: AsyncSession = Depends(async_get_db)): # Use AsyncSession and async_get_db
    """
    Retrieves the current system settings (Setpoint, Timers, Fan Speeds).
    Creates default settings if none exist.
    """
    # Use the async query API: db.scalar(select(...)) or db.execute(select(...))
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt) # Use await and db.scalar for a single result

    if not settings:
        # If no settings row exists, create one with defaults from the model
        print("No settings found, creating default settings row...")
        settings = models.SystemSettings(id=1)
        db.add(settings) # db.add is synchronous
        # Commit handled by dependency, refresh needed to return the object with DB data
        # try:
        #     await db.commit()
        #     await db.refresh(settings) # Need await refresh!
        #     print("Default settings created.")
        # except Exception as e:
        #     await db.rollback()
        #     print(f"Error creating default settings: {e}")
        #     raise HTTPException(status_code=500, detail=f"Failed to create default settings: {e}")

        # If using the commit within the dependency:
        try:
            await db.commit() # Explicitly commit here as we are changing data
            await db.refresh(settings)
            print("Default settings created and committed.")
            return settings
        except Exception as e:
            await db.rollback()
            print(f"Error creating default settings: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create default settings: {e}")


    if not settings: # Should not happen after creation attempt, but safety check
         raise HTTPException(status_code=404, detail="Settings not found and could not be created")

    return settings # Return the settings object


# --- Endpoint to PATCH System Settings ---
# Change the dependency to use async_get_db and AsyncSession
@app.patch("/settings", response_model=schemas.Settings, tags=["Settings"])
async def update_settings(
    settings_update: schemas.SettingsUpdate, # Use the update schema (all fields optional)
    db: AsyncSession = Depends(async_get_db) # Use AsyncSession and async_get_db
):
    """
    Updates specific system settings based on the provided fields.
    Only updates fields included in the request body.
    """
    # Use the async query API
    stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    settings = await db.scalar(stmt) # Use await and db.scalar

    if not settings:
        # Attempt to create default settings if they don't exist before patching
        print("Settings not found during PATCH, attempting to create defaults...")
        settings = models.SystemSettings(id=1)
        db.add(settings)
        # Commit handled by dependency, refresh needed to return object
        try:
            await db.commit() # Explicitly commit here
            await db.refresh(settings)
            print("Default settings created during PATCH.")
        except Exception as e:
            await db.rollback()
            print(f"Error creating default settings during PATCH: {e}")
            raise HTTPException(status_code=500, detail=f"Settings not found and could not be created: {e}")

    if not settings: # Check again after potential creation
        raise HTTPException(status_code=404, detail="Settings not found")

    # Get updated data as dict, excluding fields that were not sent in the request
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        # Return current settings if no update data provided (PATCH allows this)
        print("PATCH request received, but no valid fields found to update.")
        return settings # Return existing settings

    updated_fields_count = 0
    # Update the fields in the database model object
    for key, value in update_data.items():
        if hasattr(settings, key):
             setattr(settings, key, value)
             updated_fields_count += 1
        else:
            print(f"Warning: Attempted to update non-existent setting field '{key}'")

    # Set updated_at manually if fields were changed
    # Note: onupdate in the model should handle this, but manual is safer
    if updated_fields_count > 0:
        settings.updated_at = datetime.now(pytz.timezone('America/Jamaica'))

    # Commit the changes. Dependency will also attempt commit, but explicit is clearer for updates.
    try:
        await db.commit()
        await db.refresh(settings)
        print(f"Successfully updated settings: {list(update_data.keys())}") # Log updated keys
        return settings
    except Exception as e:
        await db.rollback()
        print(f"Error committing updated settings: {e}")
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")


# --- Endpoint to GET System Status ---
# Change the dependency to use async_get_db and AsyncSession
@app.get("/status", response_model=schemas.SystemStatus, tags=["Status"])
async def get_system_status(db: AsyncSession = Depends(async_get_db)): # Use AsyncSession and async_get_db
    """
    Retrieves the latest sensor readings and current system settings.
    """
    # Query latest temps and solar using async queries
    temp_stmt = select(models.TemperatureReadingDB)\
                 .order_by(models.TemperatureReadingDB.timestamp.desc())\
                 .limit(8)
    latest_temps = await db.scalars(temp_stmt).all() # Use await db.scalars(...).all()

    solar_stmt = select(models.SolarPVDataDB)\
                  .order_by(models.SolarPVDataDB.timestamp.desc())\
                  .limit(1) # Limit 1 for .first()
    latest_solar = await db.scalar(solar_stmt) # Use await db.scalar(...) for first

    # Query current settings using async query (same logic as GET /settings)
    settings_stmt = select(models.SystemSettings).where(models.SystemSettings.id == 1)
    current_settings = await db.scalar(settings_stmt) # Use await db.scalar

    # If settings don't exist, attempt to create default (consistency with /settings endpoint)
    if not current_settings:
        print("Warning: Settings not found for status endpoint, attempting to create defaults.")
        try:
            settings = models.SystemSettings(id=1)
            db.add(settings)
            # Explicitly commit the creation
            await db.commit()
            await db.refresh(settings)
            current_settings = settings # Use the newly created settings
            print("Default settings created for status endpoint.")
        except Exception as e:
             await db.rollback()
             print(f"Error creating default settings for status endpoint: {e}")
             current_settings = None # Ensure it's None if creation fails

    status_data = schemas.SystemStatus(
        temperatures=latest_temps, # These are SQLAlchemy ORM objects, Pydantic with from_attributes=True handles conversion
        solar_data=latest_solar,   # SQLAlchemy ORM object
        current_settings=current_settings # SQLAlchemy ORM object (or None)
    )
    return status_data


# --- HTML Page Endpoints ---
# These typically don't interact with the DB, so no async DB changes needed here.
# Ensure your static files are accessible.
@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_index():
    # Use async os operations if reading large files, but FileResponse handles this generally
    file_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(file_path)

# Redirect /index to /
@app.get("/index", include_in_schema=False)
async def redirect_index():
    return RedirectResponse(url="/")

# Add explicit route for /temperatures
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

# Add explicit route for /pv_info
@app.get("/pv_info", response_class=FileResponse, include_in_schema=False)
async def read_pv_info():
    file_path = os.path.join(STATIC_DIR, "pv_info.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="pv_info.html not found")
    return FileResponse(file_path)


# --- MOUNT STATIC DIRECTORY (mount last, generally) ---
# This makes files like style.css and script.js accessible via /static/filename.ext
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# ------------------------------------------------------

# --- TODO: Add endpoints for FanControl and PeltierControl if needed ---
# ... (Logic for controlling hardware - these might use asyncio or external libraries
# to communicate with your control logic, and potentially update settings in the DB)
# For example, a POST to /control/fans might update the settings in the DB.