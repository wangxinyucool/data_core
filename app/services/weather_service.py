import requests
import datetime
import time
from cachetools import TTLCache
from app.config import settings

# --- 缓存设置 ---
weather_cache = TTLCache(maxsize=128, ttl=900)
history_cache = TTLCache(maxsize=256, ttl=21600)

# 使用 requests.Session() 可以复用TCP连接，提升性能
session = requests.Session()


def _get_coords_for_city(city: str) -> dict | None:
    """内部使用的函数，将城市名转换为经纬度，并带缓存"""
    cache_key = f"coords_{city}"
    if cache_key in weather_cache:
        return weather_cache[cache_key]

    GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
    geo_params = {'q': city, 'limit': 1, 'appid': settings.API_KEY}
    try:
        res = session.get(GEO_URL, params=geo_params)
        res.raise_for_status()
        geo_data = res.json()
        if not geo_data:
            return None

        coords = {'lat': geo_data[0]['lat'], 'lon': geo_data[0]['lon']}
        weather_cache[cache_key] = coords
        return coords
    except requests.exceptions.RequestException as e:
        print(f"获取经纬度失败: {e}")
        return None


def get_realtime_weather_bundle(city: str) -> dict | None:
    """获取“实时天气”页面所需的数据包"""
    bundle_cache_key = f"bundle_{city}"
    if bundle_cache_key in weather_cache:
        print(f"从缓存读取 {city} 的实时天气数据包")
        return weather_cache[bundle_cache_key]

    coords = _get_coords_for_city(city)
    if not coords:
        return None

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    params = {**coords, 'appid': settings.API_KEY, 'units': 'metric', 'lang': 'zh_cn'}

    try:
        print(f"从API获取 {city} 的新实时天气数据包...")
        current_res = session.get(f"{BASE_URL}/weather", params=params)
        current_res.raise_for_status()

        forecast_res = session.get(f"{BASE_URL}/forecast", params=params)
        forecast_res.raise_for_status()

        air_res = session.get(f"{BASE_URL}/air_pollution", params=params)
        air_res.raise_for_status()

        result = {
            "current": current_res.json(),
            "forecast": forecast_res.json(),
            "air_quality": air_res.json()
        }
        weather_cache[bundle_cache_key] = result
        return result
    except requests.exceptions.RequestException as e:
        print(f"请求实时天气数据包失败: {e}")
        return None


def get_historical_weather(city: str, date_str: str) -> dict | None:
    """获取指定城市在过去某一日期的24小时历史天气数据。"""
    cache_key = f"history_{city}_{date_str}"
    if cache_key in history_cache:
        print(f"从缓存读取 {city} 在 {date_str} 的历史天气")
        return history_cache[cache_key]

    try:
        start_dt_object = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        start_unix_timestamp = int(start_dt_object.timestamp())
        end_dt_object = start_dt_object.replace(hour=23, minute=59, second=59)
        end_unix_timestamp = int(end_dt_object.timestamp())
    except ValueError:
        print(f"日期格式错误: {date_str}")
        return None

    coords = _get_coords_for_city(city)
    if not coords:
        return None

    HISTORY_URL = "https://history.openweathermap.org/data/2.5/history/city"
    params = {
        **coords,
        'type': 'hour',
        'start': start_unix_timestamp,
        'end': end_unix_timestamp,
        'appid': settings.API_KEY,
        'units': 'metric',
        'lang': 'zh_cn'
    }

    try:
        print(f"从正确的API({HISTORY_URL})获取 {city} 在 {date_str} 的历史天气...")
        res = session.get(HISTORY_URL, params=params)
        res.raise_for_status()
        data = res.json()
        history_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"请求历史天气失败: {e}")
        return None


def get_30_day_forecast(city: str) -> dict | None:
    """获取指定城市的30天预报数据"""
    cache_key = f"forecast30_{city}"
    if cache_key in weather_cache:
        print(f"从缓存读取 {city} 的30天预报")
        return weather_cache[cache_key]

    coords = _get_coords_for_city(city)
    if not coords:
        return None

    FORECAST_URL = "https://pro.openweathermap.org/data/2.5/forecast/climate"
    params = {
        **coords,
        'appid': settings.API_KEY,
        'units': 'metric',
        'lang': 'zh_cn'
    }

    try:
        print(f"从API获取 {city} 的30天预报...")
        res = session.get(FORECAST_URL, params=params)
        res.raise_for_status()
        data = res.json()
        weather_cache[cache_key] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"请求30天预报失败: {e}")
        return None


def get_map_layer_urls() -> dict:
    """
    构建并返回各种天气图层的URL模板。
    这些URL将由前端的地图库使用。
    """
    BASE_MAP_URL_TEMPLATE = "https://maps.openweathermap.org/maps/2.0/weather/{op}/{z}/{x}/{y}?appid={api_key}"

    layers = {
        "precipitation": "PR0",  # 降水
        "temperature": "TA2",   # 温度
        "clouds": "CL",         # 云图
        "wind_speed": "WS10",   # 风速
        "pressure": "APM",      # 气压
    }

    layer_urls = {}
    for name, op_code in layers.items():
        layer_urls[name] = BASE_MAP_URL_TEMPLATE.format(
            op=op_code,
            z="{z}",
            x="{x}",
            y="{y}",
            api_key=settings.API_KEY
        )
    return layer_urls
