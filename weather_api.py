import requests
from datetime import datetime, timedelta

class WeatherAPI:
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    historical_url = "https://archive-api.open-meteo.com/v1/archive"
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    

    @staticmethod
    def get_coordinates(city: str) -> tuple:
        params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        response = requests.get(WeatherAPI.geocode_url, params = params, timeout = 1000)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            lat = data["results"][0]["latitude"]
            lon = data["results"][0]["longitude"]
            return lat, lon
        else:
            raise ValueError(f"City '{city}' not found")
        
    @staticmethod
    def get_current_weather(city: str, hourly: list = ["temperature_2m", "precipitation", "snowfall", "relative_humidity_2m", "cloudcover", "windspeed_10m"], daily: list = None):
        lat, lon = WeatherAPI.get_coordinates(city)
        today = datetime.now().date().strftime("%Y-%m-%d")
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "start_date": today,
            "end_date": today,
        }
        if hourly:
            params["hourly"] = ",".join(hourly)
        if daily:
            params["daily"] = ",".join(daily)
        response = requests.get(WeatherAPI.forecast_url, params = params, timeout = 10000, verify = False)
        response.raise_for_status()
        response
        return response.json()

    @staticmethod
    def get_historical_weather(city: str, date: str, hourly: list = ["temperature_2m", "precipitation", "rain", "snowfall", "relative_humidity_2m", "cloudcover", "windspeed_10m"], daily: list = None):
        lat, lon = WeatherAPI.get_coordinates(city)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": date,
            "end_date": date,
            "timezone": "auto"
        }
        if hourly:
            params["hourly"] = ",".join(hourly)
        if daily:
            params["daily"] = ",".join(daily)

        response = requests.get(WeatherAPI.historical_url, params = params, verify = False)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_forecast(city: str, date: str, hourly: list = ["temperature_2m", "precipitation", "rain", "snowfall", "relative_humidity_2m", "cloudcover", "windspeed_10m"], daily: list = None):
        lat, lon = WeatherAPI.get_coordinates(city)
        today = datetime.now().date()
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        if target_date < today:
            raise ValueError("Forecast data is not available for past dates. Use get_historical_weather instead.")
        elif target_date > today + timedelta(days=16):
            raise ValueError("Forecast data is only available for up to 16 days into the future.")

        days_ahead = (target_date - today).days
        params = {
            "latitude": lat,
            "longitude": lon,
            "forecast_days": days_ahead + 1,
            "timezone": "auto"
        }
        if hourly:
            params["hourly"] = ",".join(hourly)
        if daily:
            params["daily"] = ",".join(daily)

        response = requests.get(WeatherAPI.forecast_url, params = params, timeout = 1000, verify = False)
        response.raise_for_status()
        forecast_data = response.json()

        # Extract data for the specific date
        if daily:
            daily_data = forecast_data.get("daily", {})
            date_index = daily_data.get("time", []).index(date) if date in daily_data.get("time", []) else None
            if date_index is not None:
                for key in daily_data:
                    daily_data[key] = daily_data[key][date_index:date_index + 1]
            else:
                daily_data = {}
            forecast_data["daily"] = daily_data

        if hourly:
            hourly_data = forecast_data.get("hourly", {})
            hourly_times = hourly_data.get("time", [])
            start_index = next((i for i, t in enumerate(hourly_times) if t.startswith(date)), None)
            end_index = next((i for i, t in enumerate(hourly_times) if not t.startswith(date) and i > start_index), len(hourly_times))
            if start_index is not None:
                for key in hourly_data:
                    hourly_data[key] = hourly_data[key][start_index:end_index]
            else:
                hourly_data = {}
            forecast_data["hourly"] = hourly_data

        return forecast_data