# =========================================================
# FILE: fr_sel_preset.py
# =========================================================

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
        "defaults": {
            "best_eirp_dbw": 53.50,
            "att_dl_db": 0.25,
            "att_ul_db": 0.25,
        }
    },
    "C Band": {
        "frequency_ghz": {"uplink": 6.875, "downlink": 4.650},
        "defaults": {
            "best_eirp_dbw": 41.00,
            "att_dl_db": 0.10,
            "att_ul_db": 0.10,
        }
    }
}
