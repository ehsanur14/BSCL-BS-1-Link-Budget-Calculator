# =========================================================
# FILE: calculating_ele_azi.py
# =========================================================

import math

EARTH_RADIUS_KM = 6378.137
GEO_RADIUS_KM = 42164.0

def validate_coordinates(lat_deg, lon_deg):
    try:
        return lat_deg is not None and lon_deg is not None and -90 <= float(lat_deg) <= 90 and -180 <= float(lon_deg) <= 180
    except Exception:
        return False

def normalize_angle_360(angle_deg):
    return angle_deg % 360.0

def calculate_azimuth_elevation(lat_deg, lon_deg, sat_lon_deg):
    if not validate_coordinates(lat_deg, lon_deg):
        raise ValueError("Invalid latitude or longitude.")

    delta_lon_deg = lon_deg - sat_lon_deg
    sin_lat = math.sin(math.radians(lat_deg))
    if abs(sin_lat) < 1e-12:
        raise ValueError("Latitude too close to 0° for this azimuth formula.")

    az_part = math.degrees(math.atan(math.tan(math.radians(delta_lon_deg)) / sin_lat))

    if lat_deg < 0:
        azimuth_deg = az_part if delta_lon_deg < 0 else 360 - az_part
    else:
        azimuth_deg = 180 + az_part if delta_lon_deg < 0 else 180 - az_part

    lat_rad = math.radians(lat_deg)
    delta_lon_rad = math.radians(sat_lon_deg - lon_deg)
    cos_psi = math.cos(lat_rad) * math.cos(delta_lon_rad)
    ratio = EARTH_RADIUS_KM / GEO_RADIUS_KM
    numerator = cos_psi - ratio
    denominator = math.sqrt(max(1e-12, 1 - cos_psi**2))
    elevation_deg = math.degrees(math.atan2(numerator, denominator))

    return normalize_angle_360(azimuth_deg), elevation_deg

def calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg):
    if not validate_coordinates(lat_deg, lon_deg):
        raise ValueError("Invalid latitude or longitude.")
    lat_rad = math.radians(lat_deg)
    dlon_rad = math.radians(sat_lon_deg - lon_deg)
    cos_psi = math.cos(lat_rad) * math.cos(dlon_rad)
    r_e = EARTH_RADIUS_KM
    r_s = GEO_RADIUS_KM
    return math.sqrt(r_e**2 + r_s**2 - 2 * r_e * r_s * cos_psi)

def calculate_for_dashboard(lat_deg, lon_deg, sat_lon_deg):
    az_deg, el_deg = calculate_azimuth_elevation(lat_deg, lon_deg, sat_lon_deg)
    sr_km = calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg)
    return {
        "azimuth_deg": round(az_deg, 2),
        "elevation_deg": round(el_deg, 2),
        "slant_range_km": round(sr_km, 2),
    }