import math
from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from database import get_postgres_connection
from models import SensorData, AQIRealtime, place, time, AirQuality
from models import AirQualityFULL

from datetime import datetime, timedelta
# Initialize start time when server starts
start_time = datetime(2025, 11, 3, 11, 0, 0)
server_start_time = datetime.now()

def get_simulated_time():
    """
    Returns simulated time starting from 2025-11-03 14:00:00+00
    and incrementing in real-time since server start
    """
    elapsed = datetime.now() - server_start_time
    return start_time + elapsed



app = FastAPI()

# Allow CORS for your frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        simulated_datetime = get_simulated_time()
        return time(time=simulated_datetime)
    

@app.get("/get_place_with_current_aqi")
def get_place_with_current_aqi() -> List[AirQuality]:
    conn = get_postgres_connection()
    simulated_datetime = get_simulated_time()
    query = "SELECT DISTINCT ON (province_name) province_name, latitude, longitude, pm25, pm10, vn_aqi, timestamp FROM air_quality WHERE timestamp < %s ORDER BY province_name, timestamp DESC;"
    with conn.cursor() as cursor:
        cursor.execute(query, (simulated_datetime,))
        results = cursor.fetchall()
    conn.close()
    return [AirQuality(province_name=row[0], latitude=row[1], longitude=row[2], pm25=row[3], pm10=row[4], vn_aqi=row[5], timestamp=row[6]) for row in results]


@app.get('/get_hourly_data')
def get_hourly_data(q: str) -> List[AirQualityFULL]:
    conn = get_postgres_connection()
    
    simulated_datetime = get_simulated_time()
    
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
  AND timestamp BETWEEN (TIMESTAMP '2025-03-11 12:00:00' - INTERVAL '24 hours') 
                    AND TIMESTAMP '2025-03-11 12:00:00'
GROUP BY hour
ORDER BY hour DESC"""
    
    # Thực thi truy vấn SQL với tham số q (tên tỉnh/thành phố)
    with conn.cursor() as cursor:
        cursor.execute(query, (q, ))
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
        
    # In kết quả đã xử lý để debug
    
    return [AirQualityFULL(
        province_name=q,
        latitude=row[4],
        longitude=row[3],
        pm25=row[9],
        co=row[5],
        no2=row[6],
        o3=row[7],
        so2=row[10],
        pm10=row[9],
        vn_aqi=row[1],
        timestamp=row[0]
    ) for row in processed_results]

