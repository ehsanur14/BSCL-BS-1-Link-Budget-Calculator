# =========================================================
# FILE: dashboard.py
# =========================================================

import csv
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium

st.set_page_config(page_title="Link Budget Calculations (BS-1)", layout="wide", initial_sidebar_state="collapsed")

SATELLITE_NAME = "BS-1"
OUTPUT_KEYS = ("useful_eirp_dbw", "cni_db", "modcod", "expected_datarate_mbps")
POSITION_KEYS = ("azimuth_deg", "elevation_deg", "slant_range_km")
EMPTY_OUTPUT = dict.fromkeys(OUTPUT_KEYS)
EMPTY_POSITION = dict.fromkeys(POSITION_KEYS, "")

SATELLITE_PRESETS = {
    "BS-1": {"orbital_longitude_deg": 119.1}
}

BSCL_LOCATIONS = {
    "Gazipur": {"longitude": 90.996, "latitude": 23.996},
    "Betbunia": {"longitude": 91.996, "latitude": 22.549},
}

DIVISIONAL_CITY_LOCATIONS = {
    "Dhaka": {"longitude": 90.4125, "latitude": 23.8103},
    "Chattogram": {"longitude": 91.7832, "latitude": 22.3569},
    "Rajshahi": {"longitude": 88.6042, "latitude": 24.3745},
    "Khulna": {"longitude": 89.5403, "latitude": 22.8456},
    "Barishal": {"longitude": 90.3535, "latitude": 22.7010},
    "Sylhet": {"longitude": 91.8687, "latitude": 24.8949},
    "Rangpur": {"longitude": 89.2752, "latitude": 25.7439},
    "Mymensingh": {"longitude": 90.4203, "latitude": 24.7471},
}

BAND_DEFAULTS = {
    "Ku Band": {
        "frequency_ghz": {"uplink": 13.000, "downlink": 11.075},
        "defaults": {"best_eirp_dbw": 53.50, "att_dl_db": 0.25, "att_ul_db": 0.25},
    },
    "C Band": {
        "frequency_ghz": {"uplink": 6.875, "downlink": 4.650},
        "defaults": {"best_eirp_dbw": 41.00, "att_dl_db": 0.10, "att_ul_db": 0.10},
    },
}

EARTH_RADIUS_KM = 6378.137
GEO_RADIUS_KM = 42164.0
C_LIGHT_MPS = 300_000_000.0
BOLTZMANN_DB = 228.6
DEFAULT_ROLL_OFF = 0.20
DEFAULT_THRESHOLD_KM = 300.0
KU_BAND_EIRP_CSVS = {
    "bangladesh": Path("KuBDband.csv"),
    "india": Path("KuINDband.csv"),
    "indiaplus": Path("KuINDband.csv"),
    "philippines": Path("KuPHPband.csv"),
}

KU_BAND_CONTOUR_DB: List[Dict[str, Any]] = [
    {"gateway":"GAZIPUR","country":"Bangladesh","longitude":90.996,"latitude":23.996,"att_dl":0.15,"att_ul":0.21,"best_eirp":60.80},
    {"gateway":"BETBUNIA","country":"Bangladesh","longitude":91.996,"latitude":22.549,"att_dl":0.15,"att_ul":0.21,"best_eirp":60.80},
    {"gateway":"Dhaka","country":"Bangladesh","longitude":90.410,"latitude":23.710,"att_dl":0.16,"att_ul":0.21,"best_eirp":60.80},
    {"gateway":"Chittagong","country":"Bangladesh","longitude":91.830,"latitude":22.330,"att_dl":0.15,"att_ul":0.21,"best_eirp":60.80},
    {"gateway":"Rajshahi","country":"Bangladesh","longitude":88.600,"latitude":24.370,"att_dl":0.17,"att_ul":0.22,"best_eirp":60.80},
    {"gateway":"Sylhet","country":"Bangladesh","longitude":91.870,"latitude":24.900,"att_dl":0.15,"att_ul":0.21,"best_eirp":60.80},
    {"gateway":"Mumbai","country":"IndiaPlus","longitude":72.830,"latitude":18.980,"att_dl":0.19,"att_ul":0.31,"best_eirp":53.50},
    {"gateway":"Delhi","country":"IndiaPlus","longitude":77.230,"latitude":28.610,"att_dl":0.19,"att_ul":0.31,"best_eirp":53.50},
    {"gateway":"Bangalore","country":"IndiaPlus","longitude":77.570,"latitude":12.970,"att_dl":0.12,"att_ul":0.20,"best_eirp":53.50},
    {"gateway":"Hyderabad","country":"IndiaPlus","longitude":78.480,"latitude":17.370,"att_dl":0.14,"att_ul":0.23,"best_eirp":53.50},
    {"gateway":"Ahmedabad","country":"IndiaPlus","longitude":72.580,"latitude":23.030,"att_dl":0.20,"att_ul":0.34,"best_eirp":53.50},
    {"gateway":"Chennai","country":"IndiaPlus","longitude":80.270,"latitude":13.080,"att_dl":0.15,"att_ul":0.24,"best_eirp":53.50},
    {"gateway":"Kolkata","country":"IndiaPlus","longitude":88.370,"latitude":22.570,"att_dl":0.16,"att_ul":0.26,"best_eirp":53.50},
    {"gateway":"Surat","country":"IndiaPlus","longitude":72.830,"latitude":21.170,"att_dl":0.20,"att_ul":0.32,"best_eirp":53.50},
    {"gateway":"Pune","country":"IndiaPlus","longitude":73.860,"latitude":18.520,"att_dl":0.15,"att_ul":0.25,"best_eirp":53.50},
    {"gateway":"Jaipur","country":"IndiaPlus","longitude":75.820,"latitude":26.930,"att_dl":0.18,"att_ul":0.30,"best_eirp":53.50},
    {"gateway":"Manila","country":"Philippines","longitude":120.970,"latitude":14.580,"att_dl":0.11,"att_ul":0.16,"best_eirp":54.80},
    {"gateway":"Jakarta","country":"Indonesia","longitude":106.800,"latitude":-6.400,"att_dl":0.10,"att_ul":0.18,"best_eirp":55.00},
    {"gateway":"Surabaya","country":"Indonesia","longitude":112.571,"latitude":-7.276,"att_dl":0.11,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Medan","country":"Indonesia","longitude":98.606,"latitude":3.634,"att_dl":0.12,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Bandung","country":"Indonesia","longitude":107.577,"latitude":-6.906,"att_dl":0.08,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Bekasi","country":"Indonesia","longitude":106.953,"latitude":-6.260,"att_dl":0.10,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Balikpapan","country":"Indonesia - East Kalimantan","longitude":116.809,"latitude":-1.245,"att_dl":0.10,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Manokwari","country":"Indonesia - West Papua","longitude":134.004,"latitude":-0.860,"att_dl":0.11,"att_ul":0.20,"best_eirp":55.00},
    {"gateway":"Singapore City","country":"Singapore","longitude":103.810,"latitude":0.830,"att_dl":0.10,"att_ul":0.20,"best_eirp":55.00},
]

C_BAND_CONTOUR_DB: List[Dict[str, Any]] = [
    {"gateway":"GAZIPUR","country":"Bangladesh","longitude":90.996,"latitude":23.996,"att_dl":0.06,"att_ul":0.08,"best_eirp":41.00},
    {"gateway":"BETBUNIA","country":"Bangladesh","longitude":91.996,"latitude":22.549,"att_dl":0.06,"att_ul":0.08,"best_eirp":41.00},
    {"gateway":"Dhaka","country":"Bangladesh","longitude":90.410,"latitude":23.710,"att_dl":0.06,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Chittagong","country":"Bangladesh","longitude":91.830,"latitude":22.330,"att_dl":0.06,"att_ul":0.08,"best_eirp":41.00},
    {"gateway":"Rajshahi","country":"Bangladesh","longitude":88.600,"latitude":24.370,"att_dl":0.07,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Sylhet","country":"Bangladesh","longitude":91.870,"latitude":24.900,"att_dl":0.07,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Khulna","country":"Bangladesh","longitude":90.414,"latitude":23.794,"att_dl":0.06,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Rangpur","country":"Bangladesh","longitude":89.193,"latitude":25.749,"att_dl":0.07,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Ahmedabad","country":"India","longitude":72.580,"latitude":23.030,"att_dl":0.09,"att_ul":0.11,"best_eirp":41.00},
    {"gateway":"Surabaya","country":"Indonesia","longitude":112.571,"latitude":-7.276,"att_dl":0.05,"att_ul":0.06,"best_eirp":41.00},
    {"gateway":"Kandahar","country":"Afghanistan","longitude":65.680,"latitude":31.635,"att_dl":0.08,"att_ul":0.09,"best_eirp":41.00},
    {"gateway":"Jayapura","country":"Indonesia","longitude":140.720,"latitude":-2.520,"att_dl":0.05,"att_ul":0.07,"best_eirp":40.20},
]

DEFAULT_FWD_ROLL_OFF = 0.20
DEFAULT_FWD_LINK_MARGIN_DB = 0.50
DEFAULT_FWD_ACM_MARGIN_DB = 0.00
DEFAULT_RTN_ROLL_OFF = 0.20
DEFAULT_RTN_LINK_MARGIN_DB = 0.50
DEFAULT_RTN_ACM_MARGIN_DB = 1.00
DEFAULT_RTN_MIN_SYMBOL_RATE_KSPS = 512.0


@dataclass(slots=True)
class LinkInputs:
    frequency_ghz: float
    bandwidth_mhz: float
    feed_power_w: float
    antenna_diameter_m: float
    slant_range_km: float
    efficiency_percent: float = 80.0
    loss_db: float = 0.5
    control_eirp_db: float = 10.0
    roll_off: float = DEFAULT_ROLL_OFF
    atmospheric_attenuation_db: float = 0.25
    gt_db_per_k: float = 15.6
    c_asi_db: float = 50.0
    c_xpi_db: float = 30.0
    c_im_db: float = 43.0
    c_cpi_db: float = 41.2
    c_i_co_cross_db: float = 38.4
    lnb_power_w: float = 0.0
    user_longitude_deg: Optional[float] = None
    user_latitude_deg: Optional[float] = None


@dataclass(slots=True)
class SatelliteInputs:
    satellite_eirp_dbw: float
    transponder_backoff_db: float = 0.7
    transponder_c_im_db: float = 20.0


@dataclass(slots=True)
class ModcodRow:
    required_cni_db: float
    modcod_label: str
    physical_eff_bits_per_symbol: float
    spectral_eff_bits_per_hz: float


FWD_MODCOD_TABLE: List[ModcodRow] = [
    ModcodRow(-0.24, "QPSK1s3", 0.634, 0.53), ModcodRow(0.70, "QPSK2s5", 0.760, 0.63),
    ModcodRow(2.20, "QPSK1s2", 0.951, 0.79), ModcodRow(3.57, "QPSK3s5", 1.141, 0.95),
    ModcodRow(4.30, "QPSK2s3", 1.267, 1.06), ModcodRow(5.23, "QPSK3s4", 1.426, 1.19),
    ModcodRow(5.88, "QPSK4s5", 1.521, 1.27), ModcodRow(6.38, "QPSK5s6", 1.584, 1.32),
    ModcodRow(6.70, "8PSK3s5", 1.711, 1.43), ModcodRow(7.80, "8PSK2s3", 1.901, 1.58),
    ModcodRow(9.11, "8PSK3s4", 2.139, 1.78), ModcodRow(10.47, "16APSK2s3", 2.535, 2.11),
    ModcodRow(11.50, "16APSK3s4", 2.852, 2.38), ModcodRow(12.35, "16APSK4s5", 3.042, 2.53),
    ModcodRow(12.74, "16APSK5s6", 3.169, 2.64), ModcodRow(13.67, "16APSK8s9", 3.380, 2.82),
]
FWD_FALLBACK = ModcodRow(-1.35, "QPSK1s4", 0.475, 0.40)
RTN_MODCOD_TABLE: List[ModcodRow] = [
    ModcodRow(0.00, "QPSK1s3", 0.63, 0.53), ModcodRow(2.30, "QPSK1s2", 0.95, 0.79),
    ModcodRow(3.90, "QPSK2s3", 1.27, 1.06), ModcodRow(5.00, "QPSK3s4", 1.43, 1.19),
    ModcodRow(6.10, "QPSK5s6", 1.58, 1.32), ModcodRow(8.20, "8PSK2s3", 1.90, 1.58),
    ModcodRow(9.30, "8PSK3s4", 2.14, 1.78), ModcodRow(11.00, "8PSK5s6", 2.38, 1.98),
    ModcodRow(11.60, "16QAM3s4", 2.85, 2.38), ModcodRow(13.00, "16QAM5s6", 3.17, 2.64),
]


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
        raise ValueError("Latitude too close to 0 degrees for this azimuth formula.")
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
    denominator = math.sqrt(max(1e-12, 1 - cos_psi ** 2))
    elevation_deg = math.degrees(math.atan2(numerator, denominator))
    return normalize_angle_360(azimuth_deg), elevation_deg


def calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg):
    if not validate_coordinates(lat_deg, lon_deg):
        raise ValueError("Invalid latitude or longitude.")
    lat_rad = math.radians(lat_deg)
    dlon_rad = math.radians(sat_lon_deg - lon_deg)
    cos_psi = math.cos(lat_rad) * math.cos(dlon_rad)
    return math.sqrt(EARTH_RADIUS_KM ** 2 + GEO_RADIUS_KM ** 2 - 2 * EARTH_RADIUS_KM * GEO_RADIUS_KM * cos_psi)


def calculate_for_dashboard(lat_deg, lon_deg, sat_lon_deg):
    az_deg, el_deg = calculate_azimuth_elevation(lat_deg, lon_deg, sat_lon_deg)
    sr_km = calculate_slant_range_km(lat_deg, lon_deg, sat_lon_deg)
    return {"azimuth_deg": round(az_deg, 2), "elevation_deg": round(el_deg, 2), "slant_range_km": round(sr_km, 2)}


def _round(v, nd=2):
    return None if v is None else round(v, nd)


def _band_key(name: str) -> str:
    return (name or "").strip().lower()


def _band_cfg(band_name: str):
    k = _band_key(band_name)
    if k == "ku band":
        return KU_BAND_CONTOUR_DB, 53.50, 0.25, 0.25
    if k == "c band":
        return C_BAND_CONTOUR_DB, 41.00, 0.10, 0.10
    raise ValueError("Unsupported band")


def watts_to_dbw(w):
    if w <= 0:
        raise ValueError("Power must be > 0")
    return 10 * math.log10(w)


def antenna_gain_db(freq_ghz, dia_m, eff_pct):
    eff = eff_pct / 100.0
    term = math.pi * dia_m * freq_ghz * 1e9 / C_LIGHT_MPS
    return 10 * math.log10(eff * term * term)


def fspl_db(freq_ghz, slant_km):
    return 92.45 + 20 * math.log10(freq_ghz) + 20 * math.log10(slant_km)


def occ_bw_hz(bw_mhz, roll_off):
    return (bw_mhz / (1 + roll_off)) * 1e6


def combine_db_inverse(*vals):
    linear = sum(10 ** (-v / 10) for v in vals if v is not None)
    return -10 * math.log10(linear) if linear > 0 else None


def haversine_distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat1 - lat2
    dlon = lon1 - lon2
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _row_value(row: Dict[str, Any], *candidates: str):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for candidate in candidates:
        value = lowered.get(candidate.lower())
        if value not in (None, ""):
            return value
    raise KeyError(f"Missing columns: {candidates}")


def load_ku_band_eirp_rows(csv_path: Path) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    if not csv_path.exists():
        return rows
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                rows.append({
                    "latitude": float(_row_value(row, "lat", "latitude")),
                    "longitude": float(_row_value(row, "lon", "long", "longitude")),
                    "eirp_dbw": float(_row_value(row, "eirp_dbw", "eirp", "eirp_db")),
                })
            except (KeyError, TypeError, ValueError):
                continue
    return rows


def resolve_ku_band_eirp_from_csv(lon_deg: float, lat_deg: float, default_eirp_dbw: float, csv_path: Optional[Path]):
    rows = load_ku_band_eirp_rows(csv_path) if csv_path is not None else []
    if not rows:
        return {"source": "default", "min_distance_km": None, "selected_row": None, "eirp_dbw": default_eirp_dbw}
    indexed_rows = []
    for index, row in enumerate(rows, start=1):
        indexed_rows.append((index, haversine_distance_km(row["latitude"], row["longitude"], lat_deg, lon_deg), row))
    index, min_distance_km, selected_row = min(indexed_rows, key=lambda item: item[1])
    return {"source": "csv", "index": index, "min_distance_km": min_distance_km, "selected_row": selected_row, "eirp_dbw": selected_row["eirp_dbw"]}


def resolve_contour_values(band_name: str, lon_deg: float, lat_deg: float, threshold_km: float = DEFAULT_THRESHOLD_KM):
    db, def_eirp, def_dl, def_ul = _band_cfg(band_name)
    rows = []
    for i, row in enumerate(db, start=1):
        rows.append((i, haversine_distance_km(row["latitude"], row["longitude"], lat_deg, lon_deg), row))
    idx, min_d, row = min(rows, key=lambda x: x[1])
    use_db = min_d <= threshold_km
    csv_path = None
    if _band_key(band_name) == "ku band" and use_db:
        csv_path = KU_BAND_EIRP_CSVS.get((row.get("country") or "").strip().lower())
    eirp_lookup = resolve_ku_band_eirp_from_csv(lon_deg, lat_deg, def_eirp, csv_path) if _band_key(band_name) == "ku band" else None
    return {
        "source": "database" if use_db else "default",
        "index": idx,
        "min_distance_km": min_d,
        "selected_row": row if use_db else None,
        "best_eirp_dbw": eirp_lookup["eirp_dbw"] if eirp_lookup is not None else (row["best_eirp"] if use_db else def_eirp),
        "eirp_source": None if eirp_lookup is None else eirp_lookup["source"],
        "eirp_csv": None if csv_path is None else csv_path.name,
        "eirp_index": None if eirp_lookup is None else eirp_lookup.get("index"),
        "eirp_min_distance_km": None if eirp_lookup is None else eirp_lookup["min_distance_km"],
        "eirp_selected_row": None if eirp_lookup is None else eirp_lookup["selected_row"],
        "att_cs_downlink_db": row["att_dl"] if use_db else def_dl,
        "att_cs_uplink_db": row["att_ul"] if use_db else def_ul,
    }


def calc_uplink(link: LinkInputs):
    gtx = antenna_gain_db(link.frequency_ghz, link.antenna_diameter_m, link.efficiency_percent)
    total_eirp = watts_to_dbw(link.feed_power_w) + gtx - link.loss_db
    eff_uplink_eirp = total_eirp - link.control_eirp_db
    c_n_db = eff_uplink_eirp - fspl_db(link.frequency_ghz, link.slant_range_km) - link.atmospheric_attenuation_db + link.gt_db_per_k + BOLTZMANN_DB - 10 * math.log10(occ_bw_hz(link.bandwidth_mhz, link.roll_off))
    cni = combine_db_inverse(c_n_db, link.c_asi_db, link.c_xpi_db, link.c_im_db, link.c_cpi_db, link.c_i_co_cross_db)
    return {"gtx_db": gtx, "total_eirp_dbw": total_eirp, "effective_uplink_eirp_dbw": eff_uplink_eirp, "fspl_db": fspl_db(link.frequency_ghz, link.slant_range_km), "c_n_db": c_n_db, "cni_db": cni}


def calc_satellite_useful_eirp(sat: SatelliteInputs, rx: LinkInputs):
    effective_sat_eirp = sat.satellite_eirp_dbw - sat.transponder_backoff_db
    useful_eirp = effective_sat_eirp - rx.loss_db
    return {"effective_satellite_eirp_dbw": effective_sat_eirp, "useful_eirp_dbw": useful_eirp}


def calc_downlink(useful_eirp_dbw, rx: LinkInputs):
    c_n_db = useful_eirp_dbw - rx.atmospheric_attenuation_db - fspl_db(rx.frequency_ghz, rx.slant_range_km) + rx.gt_db_per_k + BOLTZMANN_DB - 10 * math.log10(occ_bw_hz(rx.bandwidth_mhz, rx.roll_off))
    cni = combine_db_inverse(c_n_db, rx.c_xpi_db, rx.c_im_db, rx.c_cpi_db, rx.c_i_co_cross_db)
    return {"grx_db": antenna_gain_db(rx.frequency_ghz, rx.antenna_diameter_m, rx.efficiency_percent), "fspl_db": fspl_db(rx.frequency_ghz, rx.slant_range_km), "c_n_db": c_n_db, "cni_db": cni}


def calculate_complete_link(uplink: LinkInputs, downlink: LinkInputs, sat: SatelliteInputs):
    ul = calc_uplink(uplink)
    ue = calc_satellite_useful_eirp(sat, downlink)
    dl = calc_downlink(ue["useful_eirp_dbw"], downlink)
    eff_link_cni = combine_db_inverse(dl["cni_db"], sat.transponder_c_im_db, ul["cni_db"])
    return {
        "uplink": {k: _round(v) for k, v in ul.items()},
        "downlink": {k: _round(v) for k, v in dl.items()},
        "useful_eirp": {k: _round(v) for k, v in ue.items()},
        "output": {"useful_eirp_dbw": _round(ue["useful_eirp_dbw"]), "effective_downlink_cni_db": _round(dl["cni_db"]), "effective_link_cni_db": _round(eff_link_cni)},
    }


def calculate_forward_and_return_for_dashboard(band_name: str, forward_uplink: LinkInputs, forward_downlink: LinkInputs, forward_satellite: SatelliteInputs, return_uplink: Optional[LinkInputs] = None, return_downlink: Optional[LinkInputs] = None, return_satellite: Optional[SatelliteInputs] = None):
    try:
        if forward_downlink.user_longitude_deg is None or forward_downlink.user_latitude_deg is None:
            raise ValueError("Forward downlink contour location missing")
        f_contour = resolve_contour_values(band_name, forward_downlink.user_longitude_deg, forward_downlink.user_latitude_deg)
        f_ul = LinkInputs(**{**asdict(forward_uplink), "atmospheric_attenuation_db": f_contour["att_cs_uplink_db"]})
        f_dl = LinkInputs(**{**asdict(forward_downlink), "atmospheric_attenuation_db": f_contour["att_cs_downlink_db"]})
        f_sat = SatelliteInputs(**{**asdict(forward_satellite), "satellite_eirp_dbw": f_contour["best_eirp_dbw"]})
        f_res = calculate_complete_link(f_ul, f_dl, f_sat)
        r_res, r_contour = None, None
        if return_uplink and return_downlink and return_satellite and return_uplink.user_longitude_deg is not None and return_uplink.user_latitude_deg is not None:
            r_contour = resolve_contour_values(band_name, return_uplink.user_longitude_deg, return_uplink.user_latitude_deg)
            r_ul = LinkInputs(**{**asdict(return_uplink), "atmospheric_attenuation_db": r_contour["att_cs_uplink_db"]})
            r_dl = LinkInputs(**{**asdict(return_downlink), "atmospheric_attenuation_db": r_contour["att_cs_downlink_db"]})
            r_sat = SatelliteInputs(**{**asdict(return_satellite), "satellite_eirp_dbw": r_contour["best_eirp_dbw"]})
            r_res = calculate_complete_link(r_ul, r_dl, r_sat)
        return {
            "forward": f_res,
            "return": r_res,
            "contours": {"forward": {k: (_round(v) if isinstance(v, float) else v) for k, v in f_contour.items()}, "return": None if r_contour is None else {k: (_round(v) if isinstance(v, float) else v) for k, v in r_contour.items()}},
            "dashboard_output": {
                "forward_useful_eirp_dbw": f_res["output"]["useful_eirp_dbw"],
                "forward_effective_downlink_cni_db": f_res["output"]["effective_downlink_cni_db"],
                "forward_effective_cni_db": f_res["output"]["effective_link_cni_db"],
                "return_useful_eirp_dbw": None if r_res is None else r_res["output"]["useful_eirp_dbw"],
                "return_effective_downlink_cni_db": None if r_res is None else r_res["output"]["effective_downlink_cni_db"],
                "return_effective_cni_db": None if r_res is None else r_res["output"]["effective_link_cni_db"],
            },
        }
    except Exception:
        return {"forward": None, "return": None, "contours": {"forward": None, "return": None}, "dashboard_output": {"forward_useful_eirp_dbw": None, "forward_effective_downlink_cni_db": None, "forward_effective_cni_db": None, "return_useful_eirp_dbw": None, "return_effective_downlink_cni_db": None, "return_effective_cni_db": None}}


def _norm(direction: str) -> str:
    d = (direction or "").strip().lower()
    if d in {"fwd", "forward"}:
        return "forward"
    if d in {"rtn", "return", "reverse"}:
        return "return"
    raise ValueError("Invalid direction")


def _cfg(direction: str):
    d = _norm(direction)
    if d == "forward":
        return FWD_MODCOD_TABLE, FWD_FALLBACK, DEFAULT_FWD_ROLL_OFF, DEFAULT_FWD_LINK_MARGIN_DB, DEFAULT_FWD_ACM_MARGIN_DB, None
    return RTN_MODCOD_TABLE, None, DEFAULT_RTN_ROLL_OFF, DEFAULT_RTN_LINK_MARGIN_DB, DEFAULT_RTN_ACM_MARGIN_DB, DEFAULT_RTN_MIN_SYMBOL_RATE_KSPS


def calculate_modcod_and_bitrate(cni_db: Optional[float], bandwidth_mhz: Optional[float], direction: str, acm_margin_db: Optional[float] = None, link_margin_db: Optional[float] = None):
    try:
        if cni_db is None or bandwidth_mhz is None or bandwidth_mhz <= 0:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": None}
        table, fallback, roll_off, def_link, def_acm, min_sr = _cfg(direction)
        usable = cni_db - (def_acm if acm_margin_db is None else acm_margin_db) - (def_link if link_margin_db is None else link_margin_db)
        passed = [row for row in table if usable >= row.required_cni_db]
        row = max(passed, key=lambda item: item.required_cni_db) if passed else fallback
        if row is None:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": round(usable, 2)}
        symbol_rate_ksps = (bandwidth_mhz / (1 + roll_off)) * 1000
        if min_sr is not None and symbol_rate_ksps < min_sr:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": round(usable, 2)}
        return {"modcod": row.modcod_label, "bitrate_mbps": round(row.spectral_eff_bits_per_hz * bandwidth_mhz, 2), "usable_cni_db": round(usable, 2), "spectral_efficiency": row.spectral_eff_bits_per_hz}
    except Exception:
        return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": None}


def calculate_dashboard_modcod_outputs(forward_cni_db=None, forward_bandwidth_mhz=None, return_cni_db=None, return_bandwidth_mhz=None):
    forward = calculate_modcod_and_bitrate(forward_cni_db, forward_bandwidth_mhz, "forward")
    ret = calculate_modcod_and_bitrate(return_cni_db, return_bandwidth_mhz, "return")
    return {"forward": forward, "return": ret, "dashboard_output": {"forward_modcod": forward["modcod"], "forward_expected_bitrate_mbps": forward["bitrate_mbps"], "return_modcod": ret["modcod"], "return_expected_bitrate_mbps": ret["bitrate_mbps"]}}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def null_text(value, nd=2):
    try:
        if value is None or value == "":
            return ""
        if isinstance(value, (int, float)):
            return f"{round(value, nd):.{nd}f}"
        return str(value)
    except Exception:
        return ""


@st.cache_data(show_spinner=False)
def safe_position(lat_deg, lon_deg, sat_lon_deg):
    try:
        if not validate_coordinates(lat_deg, lon_deg):
            return EMPTY_POSITION.copy()
        return calculate_for_dashboard(lat_deg, lon_deg, sat_lon_deg)
    except Exception:
        return EMPTY_POSITION.copy()


def html_div(class_name, text):
    st.markdown(f'<div class="{class_name}">{text}</div>', unsafe_allow_html=True)


def section_bar(title):
    html_div("section-bar", title)


def subhead(title):
    html_div("subhead", title)


def info_line(text):
    html_div("info-line", text)


def compact_hr():
    st.markdown('<hr class="compact-hr">', unsafe_allow_html=True)


def map_link_row(side_prefix):
    city_options = ["Select divisional city"] + list(DIVISIONAL_CITY_LOCATIONS.keys())
    st.markdown('<div class="map-control-row">', unsafe_allow_html=True)
    button_col, dropdown_col = st.columns([1.05, 1.4], gap="small")
    with button_col:
        if st.button("Use Google Maps", key=f"open_map_{side_prefix}", use_container_width=True):
            st.session_state[f"{side_prefix}_saved_location"] = (
                float(st.session_state.get(f"{side_prefix}_lat", 23.7)),
                float(st.session_state.get(f"{side_prefix}_long", 90.4)),
            )
            st.session_state.active_map_picker = side_prefix
            st.session_state.pop(f"{side_prefix}_pending_location", None)
            st.rerun()
    with dropdown_col:
        selected_city = st.selectbox(
            "Divisional City",
            city_options,
            key=f"{side_prefix}_city_choice",
            label_visibility="collapsed",
        )

    if selected_city != "Select divisional city":
        city_location = DIVISIONAL_CITY_LOCATIONS[selected_city]
        city_coords = (city_location["latitude"], city_location["longitude"])
        current_coords = (
            float(st.session_state.get(f"{side_prefix}_lat", 23.7)),
            float(st.session_state.get(f"{side_prefix}_long", 90.4)),
        )
        if current_coords != city_coords:
            st.session_state[f"{side_prefix}_lat"] = city_coords[0]
            st.session_state[f"{side_prefix}_long"] = city_coords[1]
            st.session_state[f"{side_prefix}_saved_location"] = city_coords
            st.session_state.pop(f"{side_prefix}_pending_location", None)
            st.session_state.active_map_picker = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def read_map_coordinates(side_prefix):
    map_link_row(side_prefix)


def render_click_map(side_prefix):
    saved_location = st.session_state.get(f"{side_prefix}_saved_location")
    if saved_location is None:
        saved_location = (
            float(st.session_state.get(f"{side_prefix}_lat", 23.7)),
            float(st.session_state.get(f"{side_prefix}_long", 90.4)),
        )
    saved_lat, saved_lon = saved_location
    pending = st.session_state.get(f"{side_prefix}_pending_location")
    lat, lon = pending if pending else (saved_lat, saved_lon)

    map_mode = st.radio(
        "Location Source",
        ["Select on map", "Use current location"],
        horizontal=True,
        key=f"{side_prefix}_map_mode",
        label_visibility="collapsed",
    )

    fmap = folium.Map(location=[lat, lon], zoom_start=7, tiles="OpenStreetMap", control_scale=True)
    if map_mode == "Use current location":
        LocateControl(
            auto_start=True,
            flyTo=True,
            strings={"title": "Use current location", "popup": "Current location"},
            locate_options={"enableHighAccuracy": True},
        ).add_to(fmap)

    folium.Marker(
        [lat, lon],
        tooltip=f"{'Pending' if pending else 'Saved'}: {lat:.6f}, {lon:.6f}",
        popup=f"{lat:.6f}, {lon:.6f}",
        icon=folium.Icon(color="red" if pending else "blue", icon="map-marker"),
    ).add_to(fmap)

    map_state = st_folium(
        fmap,
        height=420,
        use_container_width=True,
        returned_objects=["last_clicked", "center"],
        key=f"{side_prefix}_map",
    )
    clicked = map_state.get("last_clicked") if map_state else None
    if clicked:
        clicked_lat = round(clicked["lat"], 6)
        clicked_lon = round(clicked["lng"], 6)
        if pending != (clicked_lat, clicked_lon):
            st.session_state[f"{side_prefix}_pending_location"] = (clicked_lat, clicked_lon)
            st.rerun()

    if map_mode == "Use current location" and map_state:
        center = map_state.get("center")
        if isinstance(center, dict) and "lat" in center and "lng" in center:
            current_lat = round(center["lat"], 6)
            current_lon = round(center["lng"], 6)
            current_location = (current_lat, current_lon)
            if pending != current_location:
                st.session_state[f"{side_prefix}_pending_location"] = current_location
                st.rerun()

    pending = st.session_state.get(f"{side_prefix}_pending_location")
    if pending:
        confirm_text = "Pinned location" if map_mode == "Select on map" else "Current location"
        st.markdown(
            f'<div class="confirm-line">{confirm_text}: {pending[0]:.6f}, {pending[1]:.6f}. Use this point?</div>',
            unsafe_allow_html=True,
        )
        yes_col, no_col = st.columns(2, gap="small")
        with yes_col:
            if st.button("Yes", key=f"confirm_map_{side_prefix}", use_container_width=True):
                st.session_state[f"{side_prefix}_lat"] = pending[0]
                st.session_state[f"{side_prefix}_long"] = pending[1]
                st.session_state[f"{side_prefix}_saved_location"] = pending
                st.session_state.pop(f"{side_prefix}_pending_location", None)
                st.session_state.active_map_picker = None
                st.rerun()
        with no_col:
            if st.button("No", key=f"reject_map_{side_prefix}", use_container_width=True):
                st.session_state.pop(f"{side_prefix}_pending_location", None)
                st.rerun()


def render_map_picker_screen(side_prefix):
    title = "Uplink Map Picker" if side_prefix == "uplink" else "Downlink Map Picker"
    st.markdown(f'<div class="map-picker-title">{title}</div>', unsafe_allow_html=True)
    if st.button("Back", key=f"back_map_{side_prefix}"):
        saved_location = st.session_state.get(f"{side_prefix}_saved_location")
        if saved_location is not None:
            st.session_state[f"{side_prefix}_lat"] = saved_location[0]
            st.session_state[f"{side_prefix}_long"] = saved_location[1]
        st.session_state.pop(f"{side_prefix}_pending_location", None)
        st.session_state.active_map_picker = None
        st.rerun()
    render_click_map(side_prefix)


def session_defaults(defaults):
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def panel_title(title, status=None):
    status_html = f'<span class="panel-status">{status}</span>' if status else ""
    st.markdown(f'<div class="panel-title-row"><div class="panel-title">{title}</div>{status_html}</div>', unsafe_allow_html=True)


def render_input_panel_header():
    title_col, button_col = st.columns([4.5, 1.1], gap="small")
    with title_col:
        st.markdown('<div class="panel-title-row"><div class="panel-title">Calculation Inputs</div></div>', unsafe_allow_html=True)
    with button_col:
        return st.button("Calculate", key="calculate_outputs_button", use_container_width=True)


def open_panel(class_name="app-panel"):
    return None


def close_panel():
    return None


def open_stat_panel(title):
    st.markdown(f'<div class="stat-panel"><div class="stat-panel-title">{title}</div>', unsafe_allow_html=True)


def open_stat_grid():
    st.markdown('<div class="stat-grid">', unsafe_allow_html=True)


def close_div():
    st.markdown("</div>", unsafe_allow_html=True)


def render_header():
    st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
    web_logo_path = Path("Web_logo.png")
    if web_logo_path.exists():
        st.image(str(web_logo_path), use_container_width=True)
    else:
        st.markdown(
            """
            <div class="hero-banner">
                <div class="hero-kicker">Bangladesh Satellite Company Limited</div>
                <div class="main-title">BS-1 Link Budget Calculator</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_top_controls():
    t1, t2, t3 = st.columns(3, gap="small")
    with t1:
        purpose = st.selectbox("Purpose", ["VSAT", "Broadcasting"])
    with t2:
        frequency_band = st.selectbox("Frequency Band", ["Ku Band", "C Band"])
    with t3:
        uplink_site = st.selectbox("Uplink Site", ["Own", "BSCL - Gazipur", "BSCL - Betbunia"])
    return purpose, frequency_band, uplink_site


def resolve_bscl_station(uplink_site):
    if not uplink_site.startswith("BSCL - "):
        return None

    station = uplink_site.replace("BSCL - ", "").strip()
    st.session_state.uplink_long = BSCL_LOCATIONS[station]["longitude"]
    st.session_state.uplink_lat = BSCL_LOCATIONS[station]["latitude"]
    return station


def render_uplink_inputs(purpose, selected_station, uplink_freq_default):
    subhead("Uplink Information")
    if selected_station is None:
        read_map_coordinates("uplink")
    else:
        info_line(f"BSCL Station: {selected_station}, Bangladesh")

    disabled = selected_station is not None
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        uplink_lon = st.number_input("Longitude (deg E)", format="%.3f", key="uplink_long", disabled=disabled)
    with c2:
        uplink_lat = st.number_input("Latitude (deg N)", format="%.3f", key="uplink_lat", disabled=disabled)
    with c3:
        st.text_input("Uplink Frequency (GHz)", value=f"{uplink_freq_default:.2f}", disabled=True)

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        bandwidth = st.number_input("Bandwidth (MHz)", value=36.0, format="%.2f", key="uplink_bw")
    with c2:
        feed_power = st.number_input(
            "Feed Power (W)",
            value=100.0 if purpose == "VSAT" else 200.0,
            format="%.2f",
            key="uplink_feed_power",
        )
    with c3:
        antenna_dia = st.number_input("Antenna Dia (m)", value=8.0, format="%.2f", key="uplink_ant_dia")

    return uplink_lon, uplink_lat, bandwidth, feed_power, antenna_dia


def render_downlink_inputs(purpose, downlink_freq_default):
    subhead("Downlink Information")
    read_map_coordinates("downlink")

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        downlink_lon = st.number_input("Longitude (deg E)", format="%.6f", key="downlink_long")
    with c2:
        downlink_lat = st.number_input("Latitude (deg N)", format="%.6f", key="downlink_lat")
    with c3:
        st.text_input("Downlink Frequency (GHz)", value=f"{downlink_freq_default:.3f}", disabled=True)

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        antenna_dia = st.number_input(
            "Antenna Dia (m)",
            value=0.70 if purpose == "VSAT" else 1.80,
            format="%.2f",
            key="downlink_ant_dia",
        )
    with c2:
        return_feed_power = (
            st.number_input("Return Feed Power (W)", value=20.0, format="%.2f", key="return_feed_power")
            if purpose == "VSAT"
            else None
        )
        if purpose != "VSAT":
            st.text_input("Service Type", value="Broadcast", disabled=True)
    with c3:
        st.markdown("")

    use_lnb = False
    fwd_rx_lnb = 0.0
    rtn_rx_lnb = 0.0

    return downlink_lon, downlink_lat, antenna_dia, return_feed_power, use_lnb, fwd_rx_lnb, rtn_rx_lnb


def render_position(title, position, prefix):
    open_stat_panel(title)
    labels = ("Azimuth (deg)", "Elevation (deg)")
    open_stat_grid()
    cols = st.columns(2, gap="small")
    for col, label, key in zip(cols, labels, POSITION_KEYS[:2]):
        with col:
            st.text_input(label, value=null_text(position[key]), disabled=True, key=f"{prefix}_{key}")
    close_div()
    close_div()


def render_output(title, output, prefix):
    open_stat_panel(title)
    labels = ("Useful EIRP (dBW)", "C/(N+I) (dB)", "Achievable MODCOD", "Expected Datarate (Mbps)")
    nds = (2, 2, 0, 2)
    top_cols = st.columns(2, gap="small")
    bottom_cols = st.columns(2, gap="small")
    cols = [top_cols[0], top_cols[1], bottom_cols[0], bottom_cols[1]]
    for col, label, key, nd in zip(cols, labels, OUTPUT_KEYS, nds):
        with col:
            st.text_input(label, value=null_text(output[key], nd), disabled=True, key=f"{prefix}_{key}")
    close_div()


def link_inputs(freq, bandwidth, power, antenna_dia, slant_range, lnb=0.0, lon=None, lat=None):
    return LinkInputs(
        frequency_ghz=freq,
        bandwidth_mhz=bandwidth,
        feed_power_w=power,
        antenna_diameter_m=antenna_dia,
        slant_range_km=slant_range,
        lnb_power_w=lnb or 0.0,
        user_longitude_deg=lon,
        user_latitude_deg=lat,
    )


def make_output(link_result, modcod_result, direction):
    dashboard = link_result["dashboard_output"]
    modcod = modcod_result["dashboard_output"]
    return {
        "useful_eirp_dbw": dashboard[f"{direction}_useful_eirp_dbw"],
        "cni_db": dashboard[f"{direction}_effective_cni_db"],
        "modcod": modcod[f"{direction}_modcod"],
        "expected_datarate_mbps": modcod[f"{direction}_expected_bitrate_mbps"],
    }


def has_visible_output(output):
    return any(output.get(key) not in (None, "") for key in OUTPUT_KEYS)


@st.cache_data(show_spinner=False)
def calculate_outputs(inputs):
    forward_output = EMPTY_OUTPUT.copy()
    return_output = EMPTY_OUTPUT.copy()
    debug_payload = {}

    try:
        has_valid_geometry = (
            validate_coordinates(inputs["uplink_lat"], inputs["uplink_lon"])
            and validate_coordinates(inputs["downlink_lat"], inputs["downlink_lon"])
            and inputs["uplink_pos"]["slant_range_km"] != ""
            and inputs["downlink_pos"]["slant_range_km"] != ""
        )
        if not has_valid_geometry:
            return forward_output, return_output, debug_payload

        forward_uplink = link_inputs(
            inputs["uplink_freq"],
            inputs["bandwidth"],
            inputs["uplink_feed_power"],
            inputs["uplink_antenna_dia"],
            inputs["uplink_pos"]["slant_range_km"],
        )
        forward_downlink = link_inputs(
            inputs["downlink_freq"],
            inputs["bandwidth"],
            1.0,
            inputs["downlink_antenna_dia"],
            inputs["downlink_pos"]["slant_range_km"],
            inputs["fwd_rx_lnb"],
            inputs["downlink_lon"],
            inputs["downlink_lat"],
        )
        forward_satellite = SatelliteInputs(satellite_eirp_dbw=inputs["band_info"]["defaults"]["best_eirp_dbw"])

        return_uplink = return_downlink = return_satellite = None
        if inputs["purpose"] == "VSAT":
            return_uplink = link_inputs(
                inputs["uplink_freq"],
                inputs["bandwidth"],
                inputs["return_feed_power"] or 0.0,
                inputs["downlink_antenna_dia"],
                inputs["downlink_pos"]["slant_range_km"],
                lon=inputs["downlink_lon"],
                lat=inputs["downlink_lat"],
            )
            return_downlink = link_inputs(
                inputs["downlink_freq"],
                inputs["bandwidth"],
                1.0,
                inputs["uplink_antenna_dia"],
                inputs["uplink_pos"]["slant_range_km"],
                inputs["rtn_rx_lnb"],
            )
            return_satellite = SatelliteInputs(satellite_eirp_dbw=inputs["band_info"]["defaults"]["best_eirp_dbw"])

        link_result = calculate_forward_and_return_for_dashboard(
            band_name=inputs["frequency_band"],
            forward_uplink=forward_uplink,
            forward_downlink=forward_downlink,
            forward_satellite=forward_satellite,
            return_uplink=return_uplink,
            return_downlink=return_downlink,
            return_satellite=return_satellite,
        )
        modcod_result = calculate_dashboard_modcod_outputs(
            forward_cni_db=link_result["dashboard_output"]["forward_effective_cni_db"],
            forward_bandwidth_mhz=inputs["bandwidth"],
            return_cni_db=link_result["dashboard_output"]["return_effective_cni_db"],
            return_bandwidth_mhz=inputs["bandwidth"] if inputs["purpose"] == "VSAT" else None,
        )

        forward_output = make_output(link_result, modcod_result, "forward")
        if inputs["purpose"] == "VSAT":
            return_output = make_output(link_result, modcod_result, "return")
        debug_payload = {"link_result": link_result, "modcod_result": modcod_result}
    except Exception as exc:
        debug_payload = {"error": str(exc)}

    return forward_output, return_output, debug_payload


@st.cache_data(show_spinner=False)
def load_logo_bytes():
    logo_path = Path("logo.png")
    return logo_path.read_bytes() if logo_path.exists() else None


# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
st.markdown("""
<style>
:root{
    --text:#24364d;
    --input:#fbf8f2;
    --bg:#f2f3f7;
    --panel:#ffffff;
    --line:#d8dee8;
    --soft:#edf3fb;
    --brand:#235f99;
    --brand-dark:#173d68;
    --chip:#e5f4e8;
    --chip-text:#4b8b57;
    --shadow:0 10px 28px rgba(31, 48, 78, .10);
}
html, body, .stApp, [data-testid="stAppViewContainer"]{
    background:linear-gradient(180deg,#f5f6fa 0%,#eef1f6 100%); color:var(--text);
}
header[data-testid="stHeader"], [data-testid="collapsedControl"]{display:none;}
.block-container{max-width:1920px;padding-top:.18rem;padding-bottom:.18rem;padding-left:.9rem;padding-right:.9rem;}
.stMarkdown p, div[data-testid="stVerticalBlock"] > div{margin-bottom:.04rem;}
.hero-shell{
    background:#02060d;
    border:1px solid #293243;
    border-radius:0;
    box-shadow:0 12px 30px rgba(10, 16, 28, .22);
    padding:.18rem .35rem;
    margin:0 0 .6rem 0;
}
.hero-logo, .hero-satellite{
    background:transparent;
    min-height:112px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.hero-logo img, .hero-satellite img{
    max-height:102px!important;
    object-fit:contain;
}
.hero-banner{
    min-height:112px;
    border:1px solid #2d3850;
    background:
        linear-gradient(180deg, rgba(4,8,18,.22), rgba(4,8,18,.22)),
        radial-gradient(circle at 18% 24%, rgba(255,255,255,.65) 1px, transparent 1.4px),
        radial-gradient(circle at 33% 70%, rgba(255,255,255,.28) 1px, transparent 1.4px),
        radial-gradient(circle at 68% 28%, rgba(255,255,255,.45) 1px, transparent 1.5px),
        radial-gradient(circle at 84% 58%, rgba(255,255,255,.20) 1px, transparent 1.5px),
        linear-gradient(135deg, #050913 0%, #0d1630 46%, #070c18 100%);
    background-size:auto, 34px 34px, 52px 52px, 46px 46px, 62px 62px, auto;
    color:#fff4cb;
    padding:.45rem 1.25rem;
    display:flex;
    flex-direction:column;
    justify-content:center;
}
.hero-kicker{
    text-transform:uppercase;
    font-size:1.08rem;
    font-weight:800;
    letter-spacing:.045em;
    color:#f3d789;
    line-height:1.1;
}
.main-title{
    font-size:clamp(2.2rem,3.6vw,4rem);
    font-weight:900;
    line-height:.95;
    text-transform:uppercase;
    color:#f7fbff;
    text-shadow:
        0 0 0 #d9e5ff,
        0 1px 0 #c8d5f0,
        0 2px 0 #b7c8ec,
        0 4px 14px rgba(0,0,0,.38);
    margin:.1rem 0 0 0;
}
.app-panel{
    background:var(--panel);
    border:1px solid var(--line);
    border-radius:22px;
    box-shadow:var(--shadow);
    padding:.8rem .85rem .72rem;
    height:100%;
}
.panel-title-row{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:.75rem;
    margin:0 0 .7rem 0;
}
.panel-title{
    font-size:1.5rem;
    font-weight:800;
    color:#27384f;
}
.panel-status{
    display:inline-flex;
    align-items:center;
    border-radius:999px;
    padding:.32rem .72rem;
    background:var(--chip);
    color:var(--chip-text);
    font-size:.78rem;
    font-weight:800;
}
.section-bar{
    width:100%;
    background:linear-gradient(180deg,#eff5fc 0%, #e4ecf8 100%);
    border:1px solid #d5deeb;
    border-radius:13px;
    color:#264260;
    font-weight:800;
    text-align:left;
    padding:.46rem .8rem;
    margin:.16rem 0 .48rem 0;
    font-size:.95rem;
}
.subhead{
    width:100%;
    background:linear-gradient(180deg,#eef3fb 0%, #e5edf8 100%);
    border:1px solid #d4ddeb;
    border-radius:12px;
    color:#293c55;
    font-weight:800;
    text-align:left;
    padding:.42rem .7rem;
    margin:.12rem 0 .34rem 0;
    font-size:.92rem;
}
.info-line{
    min-height:1.62rem;
    display:flex;
    align-items:center;
    font-size:.84rem;
    font-weight:700;
    color:#5a6b81;
    margin:0 0 .18rem 0;
}
.compact-hr{display:none;}
.map-picker-title{
    background:#eef3f8;
    border:1px solid #bcc9d7;
    border-bottom:none;
    border-radius:10px 10px 0 0;
    color:#22324a;
    font-weight:800;
    text-align:center;
    padding:.34rem .5rem;
    margin:.06rem 0 0 0;
    font-size:.9rem;
}
.stat-panel{
    background:#fff;
    border:1px solid #dde4ef;
    border-radius:18px;
    box-shadow:0 6px 18px rgba(30, 52, 89, .06);
    padding:.62rem .7rem .5rem;
    margin:.26rem 0 0 0;
}
.stat-panel-title{
    font-size:.92rem;
    font-weight:800;
    color:#2a3f5b;
    margin:0 0 .3rem 0;
}
.stat-grid{
    margin:0;
}
label, .stSelectbox label, .stTextInput label, .stNumberInput label{
    font-size:.76rem!important;
    font-weight:700!important;
    color:#3d4c62!important;
    margin-bottom:.03rem!important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] > div{
    border-radius:14px!important;
    min-height:2.42rem!important;
    border:1px solid #dfe5ee!important;
    box-shadow:none!important;
    background:#fff!important;
    font-size:.92rem!important;
}
div[data-testid="stTextInput"] input[disabled],
div[data-testid="stNumberInput"] input[disabled]{
    background-color:var(--input)!important;
    color:#27384f!important;
    -webkit-text-fill-color:#27384f!important;
    opacity:1!important;
    font-weight:800!important;
}
div[data-testid="stCheckbox"]{padding-top:.18rem;}
div[data-testid="stRadio"] label{font-weight:700!important;}
div[data-testid="stButton"] > button{
    min-height:2.45rem;
    border-radius:14px;
    border:1px solid #2f6da6;
    background:linear-gradient(180deg, #2d78ba 0%, #235f99 100%);
    color:#fff;
    font-weight:800;
    font-size:.9rem;
}
div[data-testid="stButton"] > button:hover{
    border-color:#1d507f;
    background:linear-gradient(180deg, #2a6fab 0%, #1f5689 100%);
    color:#fff;
}
div[data-testid="stButton"] > button[kind="secondary"]{
    background:#fff;
    color:#294869;
}
.map-control-row div[data-testid="stButton"] > button{
    min-height:2rem!important;
    padding:.18rem .8rem!important;
    border-radius:11px!important;
    font-size:.78rem!important;
}
.map-control-row div[data-testid="stSelectbox"] > div{
    min-height:2rem!important;
    border-radius:11px!important;
}
[data-testid="column"] > div:has(.app-panel){
    height:100%;
}
div[data-testid="stHorizontalBlock"]{
    gap:.7rem;
}
@media (max-width:900px){
    .block-container{padding-top:.25rem;}
    .panel-title{font-size:1.45rem;}
    .main-title{font-size:1.45rem;}
    .hero-kicker{font-size:.8rem;}
    .app-panel{padding:.85rem;}
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Page
# ---------------------------------------------------------
session_defaults({
    "uplink_long": 90.74,
    "uplink_lat": 23.98,
    "downlink_long": 90.99,
    "downlink_lat": 14.58,
    "uplink_city_choice": "Select divisional city",
    "downlink_city_choice": "Select divisional city",
    "uplink_saved_location": (23.98, 90.74),
    "downlink_saved_location": (14.58, 90.99),
    "active_map_picker": None,
})
st.session_state.setdefault("stored_forward_output", EMPTY_OUTPUT.copy())
st.session_state.setdefault("stored_return_output", EMPTY_OUTPUT.copy())
st.session_state.setdefault("stored_debug_payload", {})
st.session_state.setdefault("stored_inputs", None)

satellite_longitude = SATELLITE_PRESETS[SATELLITE_NAME]["orbital_longitude_deg"]

active_map_picker = st.session_state.get("active_map_picker")
if active_map_picker in {"uplink", "downlink"}:
    render_map_picker_screen(active_map_picker)
    st.stop()

render_header()
main_left, main_right = st.columns([1.28, 1.0], gap="large")
with main_left:
    open_panel()
    calculate_clicked = render_input_panel_header()
    section_bar("Calculation Inputs")
    purpose, frequency_band, uplink_site = render_top_controls()
    selected_bscl_station = resolve_bscl_station(uplink_site)

    band_info = BAND_DEFAULTS[frequency_band]
    uplink_freq_default = float(band_info["frequency_ghz"]["uplink"])
    downlink_freq_default = float(band_info["frequency_ghz"]["downlink"])

    uplink_lon, uplink_lat, uplink_bandwidth, uplink_feed_power, uplink_antenna_dia = render_uplink_inputs(
        purpose,
        selected_bscl_station,
        uplink_freq_default,
    )
    st.markdown('<div style="height:.45rem"></div>', unsafe_allow_html=True)
    downlink_lon, downlink_lat, downlink_antenna_dia, return_link_feed_power, use_lnb, fwd_rx_lnb, rtn_rx_lnb = render_downlink_inputs(
        purpose,
        downlink_freq_default,
    )
    close_panel()

if not validate_coordinates(uplink_lat, uplink_lon):
    st.warning("Uplink coordinates are outside valid range.")
if not validate_coordinates(downlink_lat, downlink_lon):
    st.warning("Downlink coordinates are outside valid range.")

uplink_pos = safe_position(uplink_lat, uplink_lon, satellite_longitude)
downlink_pos = safe_position(downlink_lat, downlink_lon, satellite_longitude)

current_inputs = {
    "purpose": purpose,
    "frequency_band": frequency_band,
    "band_info": band_info,
    "uplink_freq": uplink_freq_default,
    "downlink_freq": downlink_freq_default,
    "bandwidth": uplink_bandwidth,
    "uplink_feed_power": uplink_feed_power,
    "return_feed_power": return_link_feed_power,
    "uplink_antenna_dia": uplink_antenna_dia,
    "downlink_antenna_dia": downlink_antenna_dia,
    "fwd_rx_lnb": fwd_rx_lnb,
    "rtn_rx_lnb": rtn_rx_lnb,
    "uplink_lon": uplink_lon,
    "uplink_lat": uplink_lat,
    "downlink_lon": downlink_lon,
    "downlink_lat": downlink_lat,
    "uplink_pos": uplink_pos,
    "downlink_pos": downlink_pos,
}

if calculate_clicked:
    forward_output, return_output, debug_payload = calculate_outputs(current_inputs)
    st.session_state.stored_forward_output = forward_output
    st.session_state.stored_return_output = return_output
    st.session_state.stored_debug_payload = debug_payload
    st.session_state.stored_inputs = dict(current_inputs)

if not has_visible_output(st.session_state.stored_forward_output):
    forward_output, return_output, debug_payload = calculate_outputs(current_inputs)
    st.session_state.stored_forward_output = forward_output
    st.session_state.stored_return_output = return_output
    st.session_state.stored_debug_payload = debug_payload
    st.session_state.stored_inputs = dict(current_inputs)

inputs_are_current = st.session_state.stored_inputs == current_inputs
forward_output = st.session_state.stored_forward_output
return_output = st.session_state.stored_return_output
debug_payload = st.session_state.stored_debug_payload

with main_right:
    open_panel()
    panel_title("Outputs")
    if inputs_are_current:
        st.caption("Outputs are calculated from the current inputs.")
    else:
        st.warning("Inputs changed. Click Calculate to refresh the outputs.")
    section_bar("Antenna Positioning")
    p1, p2 = st.columns(2, gap="small")
    with p1:
        render_position("Uplink Antenna Positioning", uplink_pos, "uplink_position")
    with p2:
        render_position("Downlink Antenna Positioning", downlink_pos, "downlink_position")

    section_bar("Link Results")
    if purpose == "VSAT":
        o1, o2 = st.columns(2, gap="small")
    else:
        o1, o2 = st.container(), None

    with o1:
        render_output("Forward Link Output", forward_output, "forward_output")
    if o2 is not None:
        with o2:
            render_output("Return Link Output", return_output, "return_output")
    close_panel()
