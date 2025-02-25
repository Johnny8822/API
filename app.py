from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Define the request model
class TemperatureData(BaseModel):
    sensor_id: str
    temperature: float

# Store received temperature data
temperature_records = []

@app.post("/temperature/")
async def receive_temperature(data: List[TemperatureData]):
    try:
        for entry in data:
            temperature_records.append({"sensor_id": entry.sensor_id, "temperature": entry.temperature})
        return {"message": "Temperature data received successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/temperature/")
async def get_temperatures():
    return {"temperature_records": temperature_records}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
