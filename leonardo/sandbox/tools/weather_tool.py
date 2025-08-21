#!/usr/bin/env python3
"""
Weather Tool - Provides current weather and forecast information
One of the most popular features users request from AI assistants
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from .base_tool import BaseTool

# HTTP client imports
try:
    import aiohttp
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False
    print("aiohttp not available - install with: pip install aiohttp")


class WeatherTool(BaseTool):
    """Tool for weather information and forecasts."""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = None
        self.default_location = "San Francisco, CA"  # Fallback location
        
    async def _setup(self) -> None:
        """Setup weather API configuration."""
        # Try to get API key from config or environment
        self.api_key = self._get_config_value("weather.api_key", None)
        if not self.api_key:
            import os
            self.api_key = os.getenv("OPENWEATHER_API_KEY", None)
        
        if self.api_key:
            self.logger.info("✅ OpenWeatherMap API key configured")
        else:
            self.logger.info("⚠️ No weather API key - using mock weather data")
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute weather tool."""
        
        if tool_name == "get_weather":
            return await self._get_current_weather(args)
        elif tool_name == "get_forecast":
            return await self._get_weather_forecast(args)
        else:
            raise ValueError(f"Unknown weather tool: {tool_name}")
    
    async def _get_current_weather(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather for a location."""
        location = args.get("location", "current")
        units = args.get("units", "metric")  # metric, imperial, kelvin
        
        # Handle 'current' location
        if location == "current":
            location = self.default_location
        
        try:
            if self.api_key and HTTP_CLIENT_AVAILABLE:
                weather_data = await self._fetch_weather_api(location, units)
            else:
                weather_data = self._get_mock_weather(location, units)
            
            return self._format_current_weather(weather_data, location, units)
            
        except Exception as e:
            self.logger.error(f"Error getting weather for {location}: {e}")
            return self._get_error_weather(location, str(e))
    
    async def _get_weather_forecast(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a location."""
        location = args.get("location", "current")
        days = min(args.get("days", 3), 5)  # Limit to 5 days
        units = args.get("units", "metric")
        
        if location == "current":
            location = self.default_location
        
        try:
            if self.api_key and HTTP_CLIENT_AVAILABLE:
                forecast_data = await self._fetch_forecast_api(location, days, units)
            else:
                forecast_data = self._get_mock_forecast(location, days, units)
            
            return self._format_forecast(forecast_data, location, days, units)
            
        except Exception as e:
            self.logger.error(f"Error getting forecast for {location}: {e}")
            return self._get_error_weather(location, str(e))
    
    async def _fetch_weather_api(self, location: str, units: str) -> Dict[str, Any]:
        """Fetch weather from OpenWeatherMap API."""
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        
        params = {
            "q": location,
            "appid": self.api_key,
            "units": units
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    raise ValueError(f"Location '{location}' not found")
                else:
                    raise ValueError(f"Weather API error: {response.status}")
    
    async def _fetch_forecast_api(self, location: str, days: int, units: str) -> Dict[str, Any]:
        """Fetch forecast from OpenWeatherMap API."""
        base_url = "https://api.openweathermap.org/data/2.5/forecast"
        
        params = {
            "q": location,
            "appid": self.api_key,
            "units": units,
            "cnt": days * 8  # 8 forecasts per day (every 3 hours)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise ValueError(f"Forecast API error: {response.status}")
    
    def _get_mock_weather(self, location: str, units: str) -> Dict[str, Any]:
        """Generate mock weather data for demonstration."""
        temp_celsius = 22  # Nice moderate temperature
        
        if units == "imperial":
            temp = round(temp_celsius * 9/5 + 32)
            temp_unit = "°F"
        elif units == "kelvin":
            temp = round(temp_celsius + 273.15)
            temp_unit = "K"
        else:  # metric
            temp = temp_celsius
            temp_unit = "°C"
        
        return {
            "main": {
                "temp": temp,
                "feels_like": temp + 2,
                "humidity": 65,
                "pressure": 1013
            },
            "weather": [{
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }],
            "wind": {
                "speed": 3.5,
                "deg": 180
            },
            "name": location,
            "sys": {"country": "US"}
        }
    
    def _get_mock_forecast(self, location: str, days: int, units: str) -> Dict[str, Any]:
        """Generate mock forecast data."""
        forecasts = []
        base_temp = 22  # Celsius
        
        for day in range(days):
            temp_c = base_temp + (day * 2) - 1  # Slight variation
            
            if units == "imperial":
                temp = round(temp_c * 9/5 + 32)
            elif units == "kelvin":
                temp = round(temp_c + 273.15)
            else:
                temp = temp_c
            
            forecasts.append({
                "main": {
                    "temp": temp,
                    "temp_max": temp + 3,
                    "temp_min": temp - 5,
                    "humidity": 65 + day * 5
                },
                "weather": [{
                    "main": "Clear" if day % 2 == 0 else "Clouds",
                    "description": "clear sky" if day % 2 == 0 else "scattered clouds"
                }],
                "dt_txt": f"2024-01-{15 + day} 12:00:00"
            })
        
        return {"list": forecasts, "city": {"name": location}}
    
    def _format_current_weather(self, data: Dict[str, Any], location: str, units: str) -> Dict[str, Any]:
        """Format current weather data for response."""
        try:
            main = data["main"]
            weather = data["weather"][0]
            wind = data.get("wind", {})
            
            # Get unit symbols
            if units == "imperial":
                temp_unit = "°F"
                speed_unit = "mph"
            elif units == "kelvin":
                temp_unit = "K"
                speed_unit = "m/s"
            else:  # metric
                temp_unit = "°C"
                speed_unit = "m/s"
            
            formatted = {
                "location": location,
                "temperature": f"{int(main['temp'])}{temp_unit}",
                "feels_like": f"{int(main['feels_like'])}{temp_unit}",
                "condition": weather["description"].title(),
                "humidity": f"{main['humidity']}%",
                "wind_speed": f"{wind.get('speed', 0)} {speed_unit}",
                "summary": (
                    f"Current weather in {location}: {int(main['temp'])}{temp_unit} "
                    f"with {weather['description']}. Feels like {int(main['feels_like'])}{temp_unit}. "
                    f"Humidity is {main['humidity']}%."
                )
            }
            
            return formatted
            
        except KeyError as e:
            raise ValueError(f"Invalid weather data format: missing {e}")
    
    def _format_forecast(self, data: Dict[str, Any], location: str, days: int, units: str) -> Dict[str, Any]:
        """Format forecast data for response."""
        try:
            forecasts = data["list"]
            
            # Get unit symbol
            if units == "imperial":
                temp_unit = "°F"
            elif units == "kelvin":
                temp_unit = "K"
            else:
                temp_unit = "°C"
            
            daily_forecasts = []
            for i, forecast in enumerate(forecasts[:days]):
                main = forecast["main"]
                weather = forecast["weather"][0]
                
                daily_forecasts.append({
                    "day": f"Day {i + 1}",
                    "temperature": f"{int(main['temp'])}{temp_unit}",
                    "condition": weather["description"].title(),
                    "humidity": f"{main['humidity']}%"
                })
            
            summary_parts = []
            for forecast in daily_forecasts:
                summary_parts.append(
                    f"{forecast['day']}: {forecast['temperature']} with {forecast['condition'].lower()}"
                )
            
            return {
                "location": location,
                "days": days,
                "forecasts": daily_forecasts,
                "summary": f"Weather forecast for {location} - " + "; ".join(summary_parts) + "."
            }
            
        except KeyError as e:
            raise ValueError(f"Invalid forecast data format: missing {e}")
    
    def _get_error_weather(self, location: str, error: str) -> Dict[str, Any]:
        """Return error weather response."""
        return {
            "location": location,
            "error": error,
            "summary": f"I'm sorry, I couldn't get the weather information for {location}. {error}"
        }
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate weather tool arguments."""
        
        if tool_name in ["get_weather", "get_forecast"]:
            location = args.get("location", "current")
            if not isinstance(location, str) or len(location.strip()) == 0:
                return "Location must be a non-empty string"
            
            units = args.get("units", "metric")
            if units not in ["metric", "imperial", "kelvin"]:
                return "Units must be 'metric', 'imperial', or 'kelvin'"
        
        if tool_name == "get_forecast":
            days = args.get("days", 3)
            if not isinstance(days, int) or days < 1 or days > 5:
                return "Days must be an integer between 1 and 5"
        
        return None  # Valid
