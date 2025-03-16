from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorData(BaseModel):
    timestamp: datetime
    pm25: float
    pm10: float

    
class AQIRealtime(BaseModel):
    name: str
    lat: float | None
    lon: float | None
    pm25: float
    pm10: float
    
class place(BaseModel):
    name: str
    lat: float
    lon: float
    
class time(BaseModel):
    time: datetime
    
class AirQuality(BaseModel):
    province_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pm25: float
    pm10: float
    vn_aqi: float
    timestamp: datetime
