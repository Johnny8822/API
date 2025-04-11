# app.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime # Keep datetime import
import pytz # Keep pytz import
# Import your modules
import models
import schemas
from database import engine, get_db # Keep existing imports

# --- Creates tables including system_settings ---
models.Base.metadata.create_all(bind=engine)
# -------------------------------------------------

app = FastAPI()

# --- Existing Endpoints (/temperature, /solar_pv) ---
# ... (keep existing endpoints) ...

# --- ADD GET /settings ENDPOINT ---
@app.get("/settings", response_model=schemas.Settings)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    if not settings:
        # If no settings row exists, create one with defaults
        settings = models.SystemSettings(id=1)
        db.add(settings)
        try:
            db.commit()
            db.refresh(settings)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create default settings: {e}")
            
    if not settings: # Should not happen after creation attempt, but safety check
         raise HTTPException(status_code=404, detail="Settings not found and could not be created")
         
    return settings
# ----------------------------------

# --- ADD PATCH /settings ENDPOINT ---
@app.patch("/settings", response_model=schemas.Settings)
def update_settings(
    settings_update: schemas.SettingsUpdate, # Use the update schema (all fields optional)
    db: Session = Depends(get_db)
):
    settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    if not settings:
         # Optionally create default settings if they don't exist before patching
         settings = models.SystemSettings(id=1)
         db.add(settings)
         try:
             db.commit()
             db.refresh(settings)
         except Exception as e:
            db.rollback()
            # If creation fails maybe raise 500, or maybe 404 is still appropriate
            raise HTTPException(status_code=500, detail=f"Settings not found and could not be created: {e}")

    if not settings: # Check again after potential creation
        raise HTTPException(status_code=404, detail="Settings not found")

    # Get updated data as dict, excluding fields that were not sent in the request
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No settings provided for update")

    # Update the fields in the database model
    for key, value in update_data.items():
        setattr(settings, key, value)

    # Set updated_at manually if onupdate doesn't trigger automatically (depends on DB/SQLAlchemy version)
    settings.updated_at = datetime.now(pytz.timezone('America/Jamaica'))

    try:
        db.commit()
        db.refresh(settings)
        return settings
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database commit failed: {e}")
# -----------------------------------

# --- UPDATE GET /status ENDPOINT ---
@app.get("/status", response_model=schemas.SystemStatus)
def get_system_status(db: Session = Depends(get_db)):
    # Query latest temps and solar (keep this logic)
    latest_temps = db.query(models.TemperatureReadingDB)\
                     .order_by(models.TemperatureReadingDB.timestamp.desc())\
                     .limit(8)\
                     .all()
    latest_solar = db.query(models.SolarPVDataDB)\
                     .order_by(models.SolarPVDataDB.timestamp.desc())\
                     .first()

    # Query current settings
    current_settings = db.query(models.SystemSettings).filter(models.SystemSettings.id == 1).first()
    # Handle case where settings might not exist yet (optional, depends if GET /settings creates them)
    if not current_settings:
       # Option 1: Return None for settings
       # current_settings = None
       # Option 2: Create default (redundant if GET /settings already does this)
       current_settings = models.SystemSettings(id=1) # Return default values without saving to DB here
       # Or raise an internal error if settings should always exist
       # raise HTTPException(status_code=500, detail="System settings not initialized")


    status_data = schemas.SystemStatus(
        temperatures=latest_temps,
        solar_data=latest_solar,
        current_settings=current_settings # Pass the settings object
    )
    return status_data
# ---------------------------------

# ... (keep other endpoints if any) ...