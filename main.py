import math
from fastapi import FastAPI, HTTPException, Depends, Header
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from fastapi.middleware.cors import CORSMiddleware
from database import get_postgres_connection
from models import SensorData, AQIRealtime, place, time, AirQuality, AirQualityFULL, Forecasted_AirQuality, Predict_Model
import jwt
import json

# Initialize start time when server starts
start_time = datetime(2025, 11, 3, 11, 0, 0)
server_start_time = datetime.now() - timedelta(hours=7)


# Cấu hình sử dụng thời gian thực hay thời gian mô phỏng
USE_REAL_TIME = True

def get_current_time():
    """
    Returns either real time or simulated time based on configuration
    """
    if USE_REAL_TIME:
        return datetime.now() - timedelta(hours=7)
    else:
        elapsed = datetime.now() - timedelta(hours=7) - server_start_time
        return start_time + elapsed

app = FastAPI()

# Allow CORS for your frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Admin credentials (In production, use database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

class LoginData(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return username

@app.post("/api/admin/login")
async def admin_login(login_data: LoginData):
    if login_data.username != ADMIN_USERNAME or login_data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.username}, expires_delta=access_token_expires
    )
    return {"token": access_token}

@app.get("/api/admin/verify")
async def verify_token(current_admin: str = Depends(get_current_admin)):
    return {"status": "valid", "username": current_admin}

@app.get("/get_air_quality")
def get_air_quality(q: str) -> List[AQIRealtime]:
    conn = get_postgres_connection()
    query = "SELECT province_name, latitude, longitude, pm25, pm10, vn_aqi FROM air_quality WHERE province_name = %s"
    with conn.cursor() as cursor:
        cursor.execute(query, (q,))
        results = cursor.fetchall()
    conn.close()
    
    # Convert results to list of AQIRealtime
    air_quality_data = [AQIRealtime(name=row[0], lat=row[1], lon=row[2], pm25=row[3], pm10=row[4]) for row in results]
    return air_quality_data

@app.get("/get_place")
def get_place() -> List[place]:
    conn = get_postgres_connection()
    query = "SELECT distinct province_name, longitude, latitude from  air_quality"
    with conn.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
    conn.close()
    place_data = [place(name=row[0], lat=row[1], lon=row[2]) for row in results]
    return place_data

@app.get("/get_simulated_time")
def get_simulated_time_endpoint() -> time:
    current_time = get_current_time()
    return time(time=current_time)
    
@app.get("/get_place_with_current_aqi")
def get_place_with_current_aqi() -> List[AirQuality]:
    conn = get_postgres_connection()
    
    current_time = get_current_time()
        
    query = "SELECT DISTINCT ON (province_name) province_name, latitude, longitude, pm25, pm10, vn_aqi, timestamp FROM air_quality WHERE timestamp < %s ORDER BY province_name, timestamp DESC;"
    with conn.cursor() as cursor:
        cursor.execute(query, (current_time,))
        results = cursor.fetchall()
    conn.close()
    return [AirQuality(province_name=row[0], latitude=row[1], longitude=row[2], pm25=row[3], pm10=row[4], vn_aqi=row[5], timestamp=row[6]) for row in results]

@app.get('/get_hourly_data')
def get_hourly_data(q: str) -> List[AirQualityFULL]:
    conn = get_postgres_connection()
    
    current_time = get_current_time()
    
    query = """
    SELECT DATE_TRUNC('hour', timestamp) AS hour, 
       AVG(vn_aqi) AS avg_aqi, 
       COUNT(*) AS record_count,
       AVG(longitude) AS x,
       AVG(latitude) AS latitude,
       CASE WHEN AVG(co)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(co) END AS co,
       CASE WHEN AVG(no2)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(no2) END AS no2,
       CASE WHEN AVG(o3)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(o3) END AS o3,
       CASE WHEN AVG(pm10)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(pm10) END AS pm10,
       CASE WHEN AVG(pm25)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(pm25) END AS pm25,
       CASE WHEN AVG(so2)::text IN ('NaN', 'Infinity', '-Infinity') THEN 0 ELSE AVG(so2) END AS so2
FROM air_quality
WHERE province_name = %s
  AND timestamp BETWEEN (%s - INTERVAL '24 hours') AND %s
GROUP BY hour
ORDER BY hour DESC"""
    
    # Thực thi truy vấn SQL với tham số q (tên tỉnh/thành phố)
    with conn.cursor() as cursor:
        cursor.execute(query, (q, current_time, current_time))
        results = cursor.fetchall()
    conn.close()

    # Xử lý kết quả để thay thế các giá trị NaN hoặc Inf thành None
    # Điều này đảm bảo dữ liệu hợp lệ khi chuyển đổi thành JSON

    processed_results = []
    for row in results:
        processed_row = []
        for value in row:
            # Kiểm tra nếu giá trị là số thực và là NaN hoặc Inf
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                processed_row.append(None)  # Thay thế bằng None
            else:
                processed_row.append(value) # Giữ nguyên giá trị
        processed_results.append(processed_row)
        
    return [AirQualityFULL(
        province_name=q,
        latitude=row[4],
        longitude=row[3],
        pm25=row[9],
        co=row[5],
        no2=row[6],
        o3=row[7],
        so2=row[10],
        pm10=row[8],
        vn_aqi=row[1],
        timestamp=row[0]
    ) for row in processed_results]


@app.get("/api/forecast-aqi")
async def get_forecast_aqi(province: str):
    """
    Get AQI forecast data for a specific province.
    
    Args:
        province: The name of the province to get forecast data for
        
    Returns:
        A JSON response containing the forecast AQI data
    """
    try:
        # Connect to the database
        conn = get_postgres_connection()
        # Get current time
        current_time = datetime.now().date()
        
        # SQL query to get forecast data
        query = """
        SELECT 
            timestamp,
            aqi,
            province_name
        FROM forecast_aqi
        WHERE province_name = %s
        AND timestamp >= %s
        ORDER BY timestamp
        """
        
        with conn.cursor() as cursor:
            cursor.execute(query, (province, current_time))
            results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {"message": f"No forecast data available for {province}"}
        
        # Process results
        forecast_data = []
        for row in results:
            # Handle NaN or Inf values
            processed_values = []
            for value in row:
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    processed_values.append(None)
                else:
                    processed_values.append(value)
            
            forecast_data.append({
                "timestamp": processed_values[0],
                "aqi": processed_values[1],
                "province_name": processed_values[2],
            })
        
        return [Forecasted_AirQuality(
            province_name=row[2],
            aqi=row[1],
            timestamp=row[0]
    ) for row in forecast_data]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving forecast data: {str(e)}")


@app.get("/admin/models", response_model=list[Predict_Model])
async def get_all_models():
    """
    Retrieve all models from the database.
    This endpoint is for admin use to view all available prediction models.
    """
    try:
        conn = get_postgres_connection()
        
        # SQL query to get all models
        query = """
        SELECT 
            model,
            model_path,
            mae,
            rmse,
            r2,
            mape,
            test_loss,
            is_active,
            trained_time
        FROM model_output
        ORDER BY trained_time DESC
        """
        
        with conn.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
        conn.close()
        
        if not results:
            return []
        
        # Process results
        models_data = []
        for row in results:
            # Handle NaN or Inf values
            processed_values = []
            for value in row:
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    processed_values.append(None)
                else:
                    processed_values.append(value)
            
            models_data.append(Predict_Model(
                model=processed_values[0],
                model_path=processed_values[1],
                mae=processed_values[2],
                rmse=processed_values[3],
                r2=processed_values[4],
                mape=processed_values[5],
                test_loss=processed_values[6],
                is_active=processed_values[7],
                trained_time=processed_values[8]
            ))
        
        return models_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving models data: {str(e)}")


@app.post("/admin/activate-model")
async def activate_model(model_path:str):
    try:
        if not model_path:
            raise HTTPException(status_code=400, detail="Model ID is required")
        
        # Connect to the database
        conn = get_postgres_connection()
        
        # First, set all models to inactive
        with conn.cursor() as cursor:
            cursor.execute("UPDATE model_output SET is_active = FALSE")
        
        # Then, set the selected model to active
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE model_output SET is_active = TRUE WHERE model_path = %s",
                (model_path,)
            )
            if cursor.rowcount == 0:
                conn.close()
                raise HTTPException(status_code=404, detail="Model not found")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        return {"message": "Model activated successfully"}
    
    except Exception as e:
        # Ensure connection is closed in case of error
        if 'conn' in locals() and conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error activating model: {str(e)}")
