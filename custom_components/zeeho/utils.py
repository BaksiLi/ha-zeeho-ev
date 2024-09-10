# -*- coding: utf-8 -*-
"""Mars coordinates transform"""
import math
import time
from typing import List, Optional, Tuple

# Constants
PI = math.pi
A = 6378245.0  # Semi-major axis
EE = 0.00669342162296594323  # Flattening factor

def get_epoch_time_str() -> str:
    """Returns the current epoch time in milliseconds."""
    return str(time.time_ns())[:13]

def get_cfmoto_x_param_str(appid: str, nonce: str, timestamp: Optional[str] = None) -> str:
    """Constructs a parameter string for CFMOTO X."""
    timestamp = timestamp or get_epoch_time_str()
    return f'appID={appid}&nonce={nonce}&timestamp={timestamp}'

def wgs84togcj02(lng: float, lat: float) -> List[float]:
    """
    Converts WGS84 to GCJ02 (Mars coordinates).
    
    :param lng: Longitude in WGS84
    :param lat: Latitude in WGS84
    :return: [converted_longitude, converted_latitude]
    """
    if out_of_china(lng, lat):
        return [lng, lat]
    dlat = transformlat(lng - 105.0, lat - 35.0)
    dlng = transformlng(lng - 105.0, lat - 35.0)
    
    radlat = lat * (PI / 180.0)
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    
    return [lng + dlng, lat + dlat]

def gcj02towgs84(lng: float, lat: float) -> List[float]:
    """
    Converts GCJ02 (Mars coordinates) to GPS84.
    
    :param lng: Longitude in GCJ02
    :param lat: Latitude in GCJ02
    :return: [converted_longitude, converted_latitude]
    """
    if out_of_china(lng, lat):
        return [lng, lat]
    dlat = transformlat(lng - 105.0, lat - 35.0)
    dlng = transformlng(lng - 105.0, lat - 35.0)
    
    radlat = lat * (PI / 180.0)
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    
    return [lng * 2 - (lng + dlng), lat * 2 - (lat + dlat)]

def gcj02_to_bd09(lng: float, lat: float) -> List[float]:
    """
    Converts GCJ02 (Mars coordinates) to BD09 (Baidu coordinates).
    
    :param lng: Longitude in GCJ02
    :param lat: Latitude in GCJ02
    :return: [converted_longitude, converted_latitude]
    """
    z = math.sqrt(lng ** 2 + lat ** 2) + 0.00002 * math.sin(lat * PI)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * PI)
    
    return [
        z * math.cos(theta) + 0.0065,
        z * math.sin(theta) + 0.006
    ]

def bd09_to_gcj02(bd_lon: float, bd_lat: float) -> List[float]:
    """
    Converts BD09 (Baidu coordinates) to GCJ02 (Mars coordinates).
    
    :param bd_lon: Longitude in BD09
    :param bd_lat: Latitude in BD09
    :return: [converted_longitude, converted_latitude]
    """
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x ** 2 + y ** 2) - 0.00002 * math.sin(y * PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * PI)
    
    return [z * math.cos(theta), z * math.sin(theta)]

def bd09_to_wgs84(bd_lon: float, bd_lat: float) -> List[float]:
    """Converts BD09 to WGS84."""
    lon, lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02towgs84(lon, lat)

def wgs84_to_bd09(lon: float, lat: float) -> List[float]:
    """Converts WGS84 to BD09."""
    lon, lat = wgs84togcj02(lon, lat)
    return gcj02_to_bd09(lon, lat)

def transformlat(lng: float, lat: float) -> float:
    """Transforms latitude based on provided longitude and latitude."""
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat**2 + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 * math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320 * math.sin(lat * PI / 30.0)) * 2.0 / 3.0
    return ret

def transformlng(lng: float, lat: float) -> float:
    """Transforms longitude based on provided longitude and latitude."""
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng**2 + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * PI) + 40.0 * math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * PI) + 300.0 * math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
    return ret

def out_of_china(lng: float, lat: float) -> bool:
    """Determines whether the coordinates are outside of China."""
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)

# Example usage
if __name__ == '__main__':
    lng = 121.532
    lat = 31.256
    result1 = wgs84togcj02(lng, lat)
    result2 = gcj02towgs84(result1[0], result1[1])
    print(result1, result2)
