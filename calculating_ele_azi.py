# =========================================================
# FILE: calculating_ele_azi.py
# =========================================================

import math

EARTH_RADIUS_KM = 6378.137
GEO_RADIUS_KM = 42164.0


def validate_coordinates(lat_deg, lon_deg):
    try:
        return lat_deg is not None and lon_deg is not None and -180 <= float(lat_deg) <= 180 and -180 <= float(lon_deg) <= 180
    except Exception:
        return False


def normalize_angle_360(angle_deg):
    return angle_deg % 360.0


def calculate_azimuth_elevation(lat_deg, lon_deg, sat_lon_deg):
    if not validate_coordinates(lat_deg, lon_deg):
        raise ValueError("Invalid latitude or longitude.")

    lat_rad = math.radians(float(lat_deg))
    delta_lon_rad = math.radians(float(sat_lon_deg) - float(lon_deg))

    azimuth_deg = math.degrees(
        math.atan2(
            math.sin(delta_lon_rad),
            -math.sin(lat_rad) * math.cos(delta_lon_rad),
        )
    )

    cos_psi = math.cos(lat_rad) * math.cos(delta_lon_rad)
    ratio = EARTH_RADIUS_KM / GEO_RADIUS_KM
    numerator = cos_psi - ratio
    denominator = math.sqrt(max(1e-12, 1 - cos_psi**2))
    elevation_deg = math.degrees(math.atan2(numerator, denominator))

    return normalize_angle_360(azimuth_deg), elevation_deg


def calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg):
    if not validate_coordinates(lat_deg, lon_deg):
        raise ValueError("Invalid latitude or longitude.")

    lat_rad = math.radians(float(lat_deg))
    dlon_rad = math.radians(float(sat_lon_deg) - float(lon_deg))
    cos_psi = math.cos(lat_rad) * math.cos(dlon_rad)
    return math.sqrt(EARTH_RADIUS_KM**2 + GEO_RADIUS_KM**2 - 2 * EARTH_RADIUS_KM * GEO_RADIUS_KM * cos_psi)


def calculate_for_dashboard(lat_deg, lon_deg, sat_lon_deg):
    az_deg, el_deg = calculate_azimuth_elevation(lat_deg, lon_deg, sat_lon_deg)
    sr_km = calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg)
    return {
        "azimuth_deg": round(az_deg, 2),
        "elevation_deg": round(el_deg, 2),
        "slant_range_km": round(sr_km, 2),
    }
