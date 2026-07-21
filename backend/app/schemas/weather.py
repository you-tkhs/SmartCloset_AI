from pydantic import BaseModel


class WeatherInfo(BaseModel):
    city: str
    temp: float
    feels_like: float
    description: str
    humidity: int
    wind_speed: float
