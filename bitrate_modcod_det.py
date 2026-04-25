# =========================================================
# FILE: bitrate_modcod_det.py
# =========================================================

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

DEFAULT_FWD_ROLL_OFF = 0.20
DEFAULT_FWD_LINK_MARGIN_DB = 0.50
DEFAULT_FWD_ACM_MARGIN_DB = 0.00

DEFAULT_RTN_ROLL_OFF = 0.20
DEFAULT_RTN_LINK_MARGIN_DB = 0.50
DEFAULT_RTN_ACM_MARGIN_DB = 1.00
DEFAULT_RTN_MIN_SYMBOL_RATE_KSPS = 512.0

@dataclass(slots=True)
class ModcodRow:
    required_cni_db: float
    modcod_label: str
    physical_eff_bits_per_symbol: float
    spectral_eff_bits_per_hz: float

FWD_MODCOD_TABLE: List[ModcodRow] = [
    ModcodRow(-0.24, "QPSK1s3", 0.634, 0.53),
    ModcodRow(0.70, "QPSK2s5", 0.760, 0.63),
    ModcodRow(2.20, "QPSK1s2", 0.951, 0.79),
    ModcodRow(3.57, "QPSK3s5", 1.141, 0.95),
    ModcodRow(4.30, "QPSK2s3", 1.267, 1.06),
    ModcodRow(5.23, "QPSK3s4", 1.426, 1.19),
    ModcodRow(5.88, "QPSK4s5", 1.521, 1.27),
    ModcodRow(6.38, "QPSK5s6", 1.584, 1.32),
    ModcodRow(6.70, "8PSK3s5", 1.711, 1.43),
    ModcodRow(7.80, "8PSK2s3", 1.901, 1.58),
    ModcodRow(9.11, "8PSK3s4", 2.139, 1.78),
    ModcodRow(10.47, "16APSK2s3", 2.535, 2.11),
    ModcodRow(11.50, "16APSK3s4", 2.852, 2.38),
    ModcodRow(12.35, "16APSK4s5", 3.042, 2.53),
    ModcodRow(12.74, "16APSK5s6", 3.169, 2.64),
    ModcodRow(13.67, "16APSK8s9", 3.380, 2.82),
]
FWD_FALLBACK = ModcodRow(-1.35, "QPSK1s4", 0.475, 0.40)

RTN_MODCOD_TABLE: List[ModcodRow] = [
    ModcodRow(0.00, "QPSK1s3", 0.63, 0.53),
    ModcodRow(2.30, "QPSK1s2", 0.95, 0.79),
    ModcodRow(3.90, "QPSK2s3", 1.27, 1.06),
    ModcodRow(5.00, "QPSK3s4", 1.43, 1.19),
    ModcodRow(6.10, "QPSK5s6", 1.58, 1.32),
    ModcodRow(8.20, "8PSK2s3", 1.90, 1.58),
    ModcodRow(9.30, "8PSK3s4", 2.14, 1.78),
    ModcodRow(11.00, "8PSK5s6", 2.38, 1.98),
    ModcodRow(11.60, "16QAM3s4", 2.85, 2.38),
    ModcodRow(13.00, "16QAM5s6", 3.17, 2.64),
]

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

def calculate_modcod_and_bitrate(
    cni_db: Optional[float],
    bandwidth_mhz: Optional[float],
    direction: str,
    acm_margin_db: Optional[float] = None,
    link_margin_db: Optional[float] = None,
):
    try:
        if cni_db is None or bandwidth_mhz is None or bandwidth_mhz <= 0:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": None}

        table, fallback, roll_off, def_link, def_acm, min_sr = _cfg(direction)
        acm = def_acm if acm_margin_db is None else acm_margin_db
        lm = def_link if link_margin_db is None else link_margin_db
        usable = cni_db - acm - lm

        passed = [r for r in table if usable >= r.required_cni_db]
        row = max(passed, key=lambda x: x.required_cni_db) if passed else fallback

        if row is None:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": round(usable, 2)}

        symbol_rate_ksps = (bandwidth_mhz / (1 + roll_off)) * 1000
        if min_sr is not None and symbol_rate_ksps < min_sr:
            return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": round(usable, 2)}

        bitrate = row.spectral_eff_bits_per_hz * bandwidth_mhz
        return {
            "modcod": row.modcod_label,
            "bitrate_mbps": round(bitrate, 2),
            "usable_cni_db": round(usable, 2),
            "spectral_efficiency": row.spectral_eff_bits_per_hz,
        }
    except Exception:
        return {"modcod": None, "bitrate_mbps": None, "usable_cni_db": None}

def calculate_dashboard_modcod_outputs(
    forward_cni_db=None,
    forward_bandwidth_mhz=None,
    return_cni_db=None,
    return_bandwidth_mhz=None,
):
    f = calculate_modcod_and_bitrate(forward_cni_db, forward_bandwidth_mhz, "forward")
    r = calculate_modcod_and_bitrate(return_cni_db, return_bandwidth_mhz, "return")
    return {
        "forward": f,
        "return": r,
        "dashboard_output": {
            "forward_modcod": f["modcod"],
            "forward_expected_bitrate_mbps": f["bitrate_mbps"],
            "return_modcod": r["modcod"],
            "return_expected_bitrate_mbps": r["bitrate_mbps"],
        }
    }