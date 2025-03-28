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


class AirQualityFULL(BaseModel):
    province_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    co: float
    no2: float
    o3: float
    so2: float
    pm25: float
    pm10: float
    vn_aqi: float
    timestamp: datetime

class Forecasted_AirQuality(BaseModel):
    province_name: Optional[str] = None
    aqi: float
    timestamp: datetime
    
class Predict_Model(BaseModel):
    model: str
    model_path: str
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    mape: Optional[float] = None
    test_loss: Optional[float] = None
    is_active: bool
    trained_time: datetime
