from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List



app = FastAPI()


# Define the request model for Peltiers Module Blocks
class Temperature_Data_Peltier(BaseModel):
    sensor_id: str
    temperature: float 
    sensor_name: str
    block_state: bool


# A Class to store the sensor data that is being sent from the Atmega328p modules to the esp32 using the nrf24l01 

class Temperature_Sensor_Modules(BaseModel): 
    sensor_id_nrf: str
    temperature_nrf: float 
    sensor_name_nrf: str 


# A Class to control the state of each of the 4 fans
class Fan_Control(BaseModel): 
    fan_name: str # The name of each fan(e.g HOT_1, COLD_1, HOT_2, COLD_2)
    fan_speed: int # The speed of the fan (using pwm and it is a value from 0-100% using the mapping function)
    fan_pin: int # The pin that the fan is connected to on the ESP32
    fan_state: bool


class Pump_Control(BaseModel):
   pump_name: str
   pump_state: bool


class User_Time_Temp_Control(BaseModel):
    temperature_setpoint: float 
    air_condition_timer: int

class Solar_PV(BaseModel): 
   pv_voltage: float
   pv_current: float
   battery_voltage:float
   battery_current:float
   load_voltage:float
   load_current:float
   load_power:float
   sunlight_intensity: float


# Store received temperature data
temperature_records_peltier = [] 
temperature_records_NRF = [] 



#This request is to post temprautres from the ESP32 about the tempearutres of the peltier blocks
""" @app.post("/temperature_peltier")
async def send_temperature_peltier(data: List[Temperature_Data_Peltier]):
    try:
        for entry in data:
            temperature_records_peltier.append({"sensor_id": entry.sensor_id, "temperature": entry.temperature})
        return {"message": "Temperature data for Peltiers received successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
 """



""" @app.post("/temperature_NRF")
async def send_temperature_nrf(data: List[Temperature_Sensor_Modules]):
    try:
        for entry in data:
            temperature_records_NRF.append({"sensor_id": entry.sensor_id_nrf,"sensor_name":entry.sensor_name_nrf, "temperature": entry.temperature_nrf})
        return {"message": "Temperature data from NRFs received successfully", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) """



@app.post("/temperature_NRF") 
async def add_new_temp_NRF(request: Request): 
    new_temp_NRF = await request.json()
    
    
    if (not new_temp_NRF["sensor_id"] == "") and (not new_temp_NRF["sensor_name"] == "") and (not new_temp_NRF["temperature"] == ""):
      temperature_records_NRF.append(new_temp_NRF)
      
      return {
      "success" : True, 
      "result": new_temp_NRF     
    }
    else: 
      return {
      "success" : False, 
      "result": {
          "message": "Entry is not complete"
      }   
    } 
#Request to send all NRF temp to API and Database
@app.get("/temperature_NRF")
def get_all_NRF_temp():
    return temperature_records_NRF


#Request to view all Peltier Data entrys
@app.get("/temperature_Peltier")
def get_all_Peltier_temp():
    return temperature_records_peltier


#Request to send all Peltier data entry to API and Database
@app.post("/temperature_Peltier") 
async def add_new_temp_Peltier(request: Request): 
    add_new_Peltier = await request.json()
    temperature_records_peltier.append(add_new_Peltier)
    return {
      "sucess" : True, 
      "result": add_new_Peltier    
    }








#This request is to get the temperatures of the peltier modules
""" @app.get("/temperature_peltier/temperature")
def retrieve_temperatures_p(): 
 #return {"Temperature Of The Peliter Blocks": temperature_records_peltier}    
    temp_peltier =[]  
    for datum in temperature_records_peltier: 
        temp_peltier.append(datum["temperature"])
    return temp_peltier
 """

""" @app.get("/temperature_NRF/temperatures")
def retrieve_temperatures_mods(): 
    temp_nrf = []
    for datum in temp_nrf: 
        temp_nrf.append(datum[temperature_records_NRF])
    return temp_nrf """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
    
