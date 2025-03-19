import sqlite3
from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse

app = FastAPI(default_response_class=ORJSONResponse)

DB_NAME = "wx_api.db"


# Initialize SQLite Database
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zip_code TEXT,
                timestamp TEXT,
                status TEXT
            )
        """
        )
        conn.commit()


init_db()


# Convert ZIP code to latitude/longitude
def zip_to_latlon(zip_code: str):
    geocode_url = f"https://nominatim.openstreetmap.org/search?postalcode={zip_code}&country=US&format=json"
    response = requests.get(geocode_url, headers={"User-Agent": "FastAPI"})

    if response.status_code != 200 or not response.json():
        raise HTTPException(
            status_code=400, detail="Invalid ZIP code or geocoding failed"
        )

    data = response.json()[0]
    return data["lat"], data["lon"]


# Fetch weather data from NOAA
def get_weather(lat: str, lon: str):
    noaa_url = f"https://api.weather.gov/points/{lat},{lon}"
    response = requests.get(noaa_url)
    if response.status_code != 200:
        return {"error": "Failed to fetch NOAA gridpoint data"}
    data = response.json()
    forecast_url = data["properties"]["forecast"]

    response = requests.get(forecast_url)
    if response.status_code != 200:
        return {"error": "Failed to fetch NOAA forecast data"}

    forecast_data = response.json()
    current_weather1 = forecast_data["properties"]["periods"][0]
    time_period1 = current_weather1["name"]
    current_weather2 = forecast_data["properties"]["periods"][1]
    time_period2 = current_weather2["name"]

    return {
        "location": f"{lat}, {lon}",
        "Valid Time 1": time_period1,
        "Forecast 1": current_weather1["detailedForecast"],
        "Valid Time 2": time_period2,
        "Forecast 2": current_weather2["detailedForecast"],
    }


@app.get("/requests")
def get_recent_requests():
    """Fetches the most recent weather requests from the database."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM request_history ORDER BY timestamp DESC LIMIT 10"
            )
            requests_list = cursor.fetchall()

        return {
            "recent_requests": [
                {"id": r[0], "zip_code": r[1], "timestamp": r[2], "status": r[3]}
                for r in requests_list
            ]
        }
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}


@app.get("/{zip_code}")
def fetch_weather(zip_code: str):
    if not zip_code.isdigit() or len(zip_code) != 5:
        raise HTTPException(status_code=400, detail="Invalid ZIP code")
    timestamp = datetime.utcnow().isoformat()

    # Store request metadata (initial status: PENDING)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO request_history (zip_code, timestamp, status) VALUES (?, ?, ?)",
            (zip_code, timestamp, "PENDING"),
        )
        conn.commit()

    try:
        lat, lon = zip_to_latlon(zip_code)
        weather_data = get_weather(lat, lon)
        status = "SUCCESS"
    except HTTPException:
        weather_data = {"error": "Unable to fetch weather data"}
        status = "FAILED"

    # Update request status
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE request_history SET status = ? WHERE timestamp = ?",
            (status, timestamp),
        )
        conn.commit()

    return {"zip_code": zip_code, "weather": weather_data, "status": status}
