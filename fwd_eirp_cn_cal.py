# =========================================================
# FILE: fwd_eirp_cn_cal.py
# =========================================================

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
import csv
from typing import Any, Dict, List, Optional, Tuple
import math

C_LIGHT_MPS = 300_000_000.0
BOLTZMANN_DB = 228.6
DEFAULT_ROLL_OFF = 0.20
DEFAULT_THRESHOLD_KM = 300.0
KU_BAND_EIRP_CSVS = {
    "bangladesh": Path(__file__).with_name("KuBDband.csv"),
    "india": Path(__file__).with_name("KuINDband.csv"),
    "indiaplus": Path(__file__).with_name("KuINDband.csv"),
    "philippines": Path(__file__).with_name("KuPHPband.csv"),
}
KU_BAND_EIRP_CSV_PATHS = tuple(dict.fromkeys(KU_BAND_EIRP_CSVS.values()))

# ----------------------------
# KU BAND DATABASE
# ----------------------------
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

# ----------------------------
# C BAND DATABASE
# ----------------------------
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
    system_noise_temp_k: float = 145.0
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
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat1 - lat2
    dlon = lon1 - lon2
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))

def _row_value(row: Dict[str, Any], *candidates: str):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for candidate in candidates:
        value = lowered.get(candidate.lower())
        if value not in (None, ""):
            return value
    raise KeyError(f"Missing columns: {candidates}")

@lru_cache(maxsize=None)
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
        return {
            "source": "default",
            "min_distance_km": None,
            "selected_row": None,
            "eirp_dbw": default_eirp_dbw,
        }

    indexed_rows = []
    for index, row in enumerate(rows, start=1):
        distance_km = haversine_distance_km(row["latitude"], row["longitude"], lat_deg, lon_deg)
        indexed_rows.append((index, distance_km, row))

    index, min_distance_km, selected_row = min(indexed_rows, key=lambda item: item[1])
    return {
        "source": "csv",
        "index": index,
        "min_distance_km": min_distance_km,
        "selected_row": selected_row,
        "eirp_dbw": selected_row["eirp_dbw"],
    }

def resolve_ku_band_eirp_from_all_csvs(lon_deg: float, lat_deg: float, default_eirp_dbw: float):
    candidates = []
    for csv_path in KU_BAND_EIRP_CSV_PATHS:
        rows = load_ku_band_eirp_rows(csv_path)
        nearest = None
        for index, row in enumerate(rows, start=1):
            distance_km = haversine_distance_km(row["latitude"], row["longitude"], lat_deg, lon_deg)
            candidate = (distance_km, csv_path, index, row)
            if nearest is None or distance_km < nearest[0]:
                nearest = candidate
        if nearest is not None:
            candidates.append(nearest)

    if not candidates:
        return {
            "source": "default",
            "csv": None,
            "index": None,
            "min_distance_km": None,
            "selected_row": None,
            "eirp_dbw": default_eirp_dbw,
        }

    min_distance_km, csv_path, index, selected_row = max(candidates, key=lambda item: item[3]["eirp_dbw"])
    return {
        "source": "csv",
        "csv": csv_path.name,
        "index": index,
        "min_distance_km": min_distance_km,
        "selected_row": selected_row,
        "eirp_dbw": selected_row["eirp_dbw"],
    }

def resolve_contour_values(band_name: str, lon_deg: float, lat_deg: float, threshold_km: float = DEFAULT_THRESHOLD_KM):
    db, def_eirp, def_dl, def_ul = _band_cfg(band_name)
    rows = []
    for i, r in enumerate(db, start=1):
        d = haversine_distance_km(r["latitude"], r["longitude"], lat_deg, lon_deg)
        rows.append((i, d, r))
    idx, min_d, row = min(rows, key=lambda x: x[1])
    use_db = min_d <= threshold_km
    eirp_lookup = (
        resolve_ku_band_eirp_from_all_csvs(lon_deg, lat_deg, def_eirp)
        if _band_key(band_name) == "ku band"
        else None
    )
    return {
        "source": "database" if use_db else "default",
        "index": idx,
        "min_distance_km": min_d,
        "selected_row": row if use_db else None,
        "best_eirp_dbw": (
            eirp_lookup["eirp_dbw"]
            if eirp_lookup is not None
            else (row["best_eirp"] if use_db else def_eirp)
        ),
        "eirp_source": None if eirp_lookup is None else eirp_lookup["source"],
        "eirp_csv": None if eirp_lookup is None else eirp_lookup.get("csv"),
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
    fspl = fspl_db(link.frequency_ghz, link.slant_range_km)
    bw_hz = occ_bw_hz(link.bandwidth_mhz, link.roll_off)

    c_n_db = (
        eff_uplink_eirp
        - fspl
        - link.atmospheric_attenuation_db
        + link.gt_db_per_k
        + BOLTZMANN_DB
        - 10 * math.log10(bw_hz)
    )

    cni = combine_db_inverse(
        c_n_db,
        link.c_asi_db,
        link.c_xpi_db,
        link.c_im_db,
        link.c_cpi_db,
        link.c_i_co_cross_db
    )

    return {
        "gtx_db": gtx,
        "total_eirp_dbw": total_eirp,
        "effective_uplink_eirp_dbw": eff_uplink_eirp,
        "fspl_db": fspl,
        "c_n_db": c_n_db,
        "cni_db": cni
    }

def calc_satellite_useful_eirp(sat: SatelliteInputs, rx: LinkInputs):
    effective_sat_eirp = sat.satellite_eirp_dbw - sat.transponder_backoff_db

    useful_eirp = sat.satellite_eirp_dbw

    return {
        "effective_satellite_eirp_dbw": effective_sat_eirp,
        "useful_eirp_dbw": useful_eirp
    }

def calc_downlink(useful_eirp_dbw, rx: LinkInputs):
    grx = antenna_gain_db(rx.frequency_ghz, rx.antenna_diameter_m, rx.efficiency_percent)
    gt_db_per_k = grx - 10 * math.log10(rx.system_noise_temp_k)
    fspl = fspl_db(rx.frequency_ghz, rx.slant_range_km)
    bw_hz = occ_bw_hz(rx.bandwidth_mhz, rx.roll_off)

    c_n_db = (
        useful_eirp_dbw
        - rx.atmospheric_attenuation_db
        - fspl
        + gt_db_per_k
        + BOLTZMANN_DB
        - 10 * math.log10(bw_hz)
    )

    cni = combine_db_inverse(
        c_n_db,
        rx.c_xpi_db,
        rx.c_im_db,
        rx.c_cpi_db,
        rx.c_i_co_cross_db
    )

    return {
        "grx_db": grx,
        "gt_db_per_k": gt_db_per_k,
        "fspl_db": fspl,
        "c_n_db": c_n_db,
        "cni_db": cni
    }

def calculate_complete_link(uplink: LinkInputs, downlink: LinkInputs, sat: SatelliteInputs):
    ul = calc_uplink(uplink)
    ue = calc_satellite_useful_eirp(sat, downlink)
    dl = calc_downlink(ue["useful_eirp_dbw"], downlink)
    eff_link_cni = combine_db_inverse(dl["cni_db"], sat.transponder_c_im_db, ul["cni_db"])
    return {
        "uplink": {k: _round(v) for k, v in ul.items()},
        "downlink": {k: _round(v) for k, v in dl.items()},
        "useful_eirp": {k: _round(v) for k, v in ue.items()},
        "output": {
            "useful_eirp_dbw": _round(ue["useful_eirp_dbw"]),
            "effective_downlink_cni_db": _round(dl["cni_db"]),
            "effective_link_cni_db": _round(eff_link_cni),
        }
    }

def calculate_forward_and_return_for_dashboard(
    band_name: str,
    forward_uplink: LinkInputs,
    forward_downlink: LinkInputs,
    forward_satellite: SatelliteInputs,
    return_uplink: Optional[LinkInputs] = None,
    return_downlink: Optional[LinkInputs] = None,
    return_satellite: Optional[SatelliteInputs] = None,
):
    try:
        if forward_downlink.user_longitude_deg is None or forward_downlink.user_latitude_deg is None:
            raise ValueError("Forward downlink contour location missing")

        f_contour = resolve_contour_values(
            band_name,
            forward_downlink.user_longitude_deg,
            forward_downlink.user_latitude_deg
        )

        f_ul = LinkInputs(**{**asdict(forward_uplink), "atmospheric_attenuation_db": f_contour["att_cs_uplink_db"]})
        f_dl = LinkInputs(**{**asdict(forward_downlink), "atmospheric_attenuation_db": f_contour["att_cs_downlink_db"]})
        f_sat = SatelliteInputs(**{**asdict(forward_satellite), "satellite_eirp_dbw": f_contour["best_eirp_dbw"]})

        f_res = calculate_complete_link(f_ul, f_dl, f_sat)

        r_res, r_contour = None, None
        if return_uplink and return_downlink and return_satellite:
            return_contour_lon = return_downlink.user_longitude_deg
            return_contour_lat = return_downlink.user_latitude_deg
            if return_contour_lon is None or return_contour_lat is None:
                return_contour_lon = return_uplink.user_longitude_deg
                return_contour_lat = return_uplink.user_latitude_deg
            if return_contour_lon is None or return_contour_lat is None:
                raise ValueError("Return contour location missing")

            r_contour = resolve_contour_values(
                band_name,
                return_contour_lon,
                return_contour_lat,
            )
            r_ul = LinkInputs(**{**asdict(return_uplink), "atmospheric_attenuation_db": r_contour["att_cs_uplink_db"]})
            r_dl = LinkInputs(**{**asdict(return_downlink), "atmospheric_attenuation_db": r_contour["att_cs_downlink_db"]})
            r_sat = SatelliteInputs(**{**asdict(return_satellite), "satellite_eirp_dbw": r_contour["best_eirp_dbw"]})
            r_res = calculate_complete_link(r_ul, r_dl, r_sat)

        return {
            "forward": f_res,
            "return": r_res,
            "contours": {
                "forward": {k: (_round(v) if isinstance(v, float) else v) for k, v in f_contour.items()},
                "return": None if r_contour is None else {k: (_round(v) if isinstance(v, float) else v) for k, v in r_contour.items()},
            },
            "dashboard_output": {
                "forward_useful_eirp_dbw": f_res["output"]["useful_eirp_dbw"],
                "forward_effective_downlink_cni_db": f_res["output"]["effective_downlink_cni_db"],
                "forward_effective_cni_db": f_res["output"]["effective_link_cni_db"],
                "return_useful_eirp_dbw": None if r_res is None else r_res["output"]["useful_eirp_dbw"],
                "return_effective_downlink_cni_db": None if r_res is None else r_res["output"]["effective_downlink_cni_db"],
                "return_effective_cni_db": None if r_res is None else r_res["output"]["effective_link_cni_db"],
            }
        }
    except Exception:
        return {
            "forward": None,
            "return": None,
            "contours": {"forward": None, "return": None},
            "dashboard_output": {
                "forward_useful_eirp_dbw": None,
                "forward_effective_downlink_cni_db": None,
                "forward_effective_cni_db": None,
                "return_useful_eirp_dbw": None,
                "return_effective_downlink_cni_db": None,
                "return_effective_cni_db": None,
            }
        }
