# =========================================================
# FILE: dashboard.py
# PURPOSE:
# Minimal 1080p-friendly BS-1 link budget dashboard
# - Clean alignment
# - Compact professional layout
# - No debug/current info panel
# - GPS shown with max 3 decimals
# - Fresh reload => values stay blank until user enters/selects
# - Invalid/insufficient input => blank outputs, no crash
# =========================================================

import re
from pathlib import Path
import streamlit as st

from fr_sel_preset import BSCL_LOCATIONS, BAND_DEFAULTS, SATELLITE_PRESETS
from calculating_ele_azi import calculate_for_dashboard, validate_coordinates
from fwd_eirp_cn_cal import LinkInputs, SatelliteInputs, calculate_forward_and_return_for_dashboard
from bitrate_modcod_det import calculate_dashboard_modcod_outputs


st.set_page_config(
    page_title="Link Budget Calculations (BS-1)",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def parse_coordinates(coord_text):
    try:
        if not coord_text:
            return None, None
        nums = re.findall(r"-?\d+(?:\.\d+)?", coord_text)
        if len(nums) < 2:
            return None, None
        a, b = float(nums[0]), float(nums[1])
        lat, lon = a, b
        if abs(lat) > 90 and abs(lon) <= 90:
            lat, lon = lon, lat
        return round(lat, 3), round(lon, 3)
    except Exception:
        return None, None


def null_text(v, nd=2):
    try:
        if v in (None, ""):
            return ""
        if isinstance(v, (int, float)):
            return f"{round(v, nd):.{nd}f}"
        return str(v)
    except Exception:
        return ""


def safe_position(lat_deg, lon_deg, sat_lon_deg):
    try:
        if lat_deg is None or lon_deg is None:
            return {"azimuth_deg": "", "elevation_deg": "", "slant_range_km": ""}
        if not validate_coordinates(lat_deg, lon_deg):
            return {"azimuth_deg": "", "elevation_deg": "", "slant_range_km": ""}
        return calculate_for_dashboard(lat_deg, lon_deg, sat_lon_deg)
    except Exception:
        return {"azimuth_deg": "", "elevation_deg": "", "slant_range_km": ""}


def section_bar(title):
    st.markdown(f'<div class="section-bar">{title}</div>', unsafe_allow_html=True)


def subhead(title):
    st.markdown(f'<div class="subhead">{title}</div>', unsafe_allow_html=True)


def map_link_row(side_prefix):
    c1, c2 = st.columns([4.4, 1.6], gap="small")
    with c1:
        use_map = st.checkbox("Use Google Maps", key=f"use_map_{side_prefix}")
    with c2:
        st.markdown(
            '<div class="map-link-inline"><a href="https://www.google.com/maps" target="_blank">Open Maps ↗</a></div>',
            unsafe_allow_html=True,
        )
    return use_map


def ensure_state(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
st.markdown(
    """
<style>
:root{
    --bg:#f5efd1;
    --bg2:#f8f3de;
    --panel:#ffffff7a;
    --text:#22324a;
    --muted:#5a6472;
    --line:#d7cca4;
    --gold1:#d8c887;
    --gold2:#cfbe79;
    --blue:#dce6f1;
    --blue-b:#bcc9d7;
    --input:#eef1f5;
}

/* page */
html, body, .stApp, [data-testid="stAppViewContainer"]{
    background:linear-gradient(180deg,var(--bg) 0%, var(--bg2) 100%);
    color:var(--text);
}
header[data-testid="stHeader"],
[data-testid="collapsedControl"]{
    display:none;
}
.block-container{
    max-width:1500px;
    padding-top:.22rem;
    padding-bottom:.18rem;
}
.stMarkdown p, div[data-testid="stVerticalBlock"] > div{
    margin-bottom:0rem;
}

/* header */
.logo-box{
    margin-top:-8px;
}
.logo-box img{
    max-height:74px !important;
    object-fit:contain;
    object-position:left top;
}
.header-box{
    background:var(--panel);
    border:1px solid var(--line);
    border-radius:16px;
    padding:.42rem .90rem;
    min-height:66px;
    display:flex;
    align-items:center;
}
.main-title{
    font-size:clamp(1.55rem,2.1vw,2.35rem);
    font-weight:800;
    line-height:1;
    color:#2f3447;
    margin:0;
    letter-spacing:.1px;
}

/* bars */
.section-bar{
    width:100%;
    background:linear-gradient(135deg,var(--gold1) 0%,var(--gold2) 100%);
    border:1px solid #b7a86a;
    border-radius:11px;
    color:#183356;
    font-weight:800;
    text-align:center;
    padding:.34rem .60rem;
    margin:.10rem 0 .12rem 0;
    font-size:.95rem;
}
.subhead{
    width:100%;
    background:var(--blue);
    border:1px solid var(--blue-b);
    border-radius:10px;
    color:#22324a;
    font-weight:800;
    text-align:center;
    padding:.28rem .42rem;
    margin:.02rem 0 .05rem 0;
    font-size:.92rem;
}

/* inputs and labels */
label, .stSelectbox label, .stTextInput label, .stNumberInput label{
    font-size:.78rem !important;
    font-weight:640 !important;
    color:#344054 !important;
    margin-bottom:.02rem !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] > div{
    border-radius:10px !important;
    min-height:1.98rem !important;
    font-size:.88rem !important;
}
div[data-testid="stTextInput"] input[disabled],
div[data-testid="stNumberInput"] input[disabled]{
    background-color:var(--input) !important;
    color:#2d3748 !important;
    -webkit-text-fill-color:#2d3748 !important;
    opacity:1 !important;
}

/* checkbox + links */
div[data-testid="stCheckbox"]{
    margin-top:-.08rem;
    margin-bottom:-.10rem;
}
.map-link-inline{
    text-align:right;
    padding-top:.12rem;
    font-size:.82rem;
    white-space:nowrap;
}
.map-link-inline a{
    color:#1d4f91;
    text-decoration:none;
    font-weight:600;
}
.map-link-inline a:hover{
    text-decoration:underline;
}

/* separators */
.compact-hr{
    border:none;
    height:1px;
    background:linear-gradient(to right, transparent, #d5ca97, transparent);
    margin:.06rem 0 .08rem 0;
}

/* alignment */
div[data-testid="column"]{
    align-self:stretch;
}
.element-container{
    margin-bottom:.05rem !important;
}

/* hide step buttons feel by compact spacing */
[data-testid="stNumberInputStepUp"],
[data-testid="stNumberInputStepDown"]{
    transform:scale(.92);
}

/* responsive */
@media (max-width: 1200px){
    .main-title{font-size:1.5rem;}
}
@media (max-width: 900px){
    .header-box{min-height:58px;padding:.32rem .60rem;}
    .main-title{font-size:1.32rem;}
    .map-link-inline{text-align:left;padding-top:.08rem;}
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------
default_values = {
    "uplink_long": 90.74,
    "uplink_lat": 23.98,
    "downlink_long": 90.996,
    "downlink_lat": 14.58,
    "uplink_coord_text": "",
    "downlink_coord_text": "",
}
for k, v in default_values.items():
    ensure_state(k, v)
    if st.session_state[k] is None:
        st.session_state[k] = v

satellite_name = "BS-1"
satellite_longitude = SATELLITE_PRESETS[satellite_name]["orbital_longitude_deg"]

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
logo_path = Path("logo.png")
h1, h2 = st.columns([0.75, 9.25], gap="small")

with h1:
    if logo_path.exists():
        st.markdown('<div class="logo-box">', unsafe_allow_html=True)
        st.image(str(logo_path), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with h2:
    st.markdown(
        '<div class="header-box"><div class="main-title">Link Budget Calculations (BS-1)</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Top controls
# ---------------------------------------------------------
t1, t2, t3 = st.columns(3, gap="small")
with t1:
    purpose = st.selectbox("Purpose", ["VSAT", "Broadcasting"])
with t2:
    frequency_band = st.selectbox("Frequency Band", ["Ku Band", "C Band"])
with t3:
    uplink_site = st.selectbox("Uplink Site", ["Own", "BSCL - Gazipur", "BSCL - Betbunia"])

selected_bscl_station = None
if uplink_site.startswith("BSCL - "):
    selected_bscl_station = uplink_site.replace("BSCL - ", "").strip()
    st.session_state.uplink_long = round(BSCL_LOCATIONS[selected_bscl_station]["longitude"], 3)
    st.session_state.uplink_lat = round(BSCL_LOCATIONS[selected_bscl_station]["latitude"], 3)

band_info = BAND_DEFAULTS[frequency_band]
uplink_freq_default = float(band_info["frequency_ghz"]["uplink"])
downlink_freq_default = float(band_info["frequency_ghz"]["downlink"])

section_bar(purpose)

# ---------------------------------------------------------
# Inputs
# ---------------------------------------------------------
left_col, right_col = st.columns(2, gap="small")

with left_col:
    subhead("Uplink Information")

    if selected_bscl_station is None:
        use_map_uplink = map_link_row("uplink")
        if use_map_uplink:
            uplink_coord_text = st.text_input(
                "Map Coordinate / Link",
                placeholder="24.000, 90.740 or paste Google Maps link",
                key="uplink_coord_text",
            )
            lat, lon = parse_coordinates(uplink_coord_text)
            if lat is not None and lon is not None:
                st.session_state.uplink_lat = lat
                st.session_state.uplink_long = lon
    else:
        st.caption(f"Preset station: {selected_bscl_station}")

    ul1, ul2, ul3 = st.columns(3, gap="small")
    with ul1:
        uplink_long = st.number_input(
            "Longitude (°E)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            key="uplink_long",
            disabled=(selected_bscl_station is not None),
            placeholder="90.740",
        )
    with ul2:
        uplink_lat = st.number_input(
            "Latitude (°N)",
            min_value=-90.0,
            max_value=90.0,
            format="%.3f",
            key="uplink_lat",
            disabled=(selected_bscl_station is not None),
            placeholder="23.980",
        )
    with ul3:
        st.text_input("Uplink Frequency (GHz)", value=f"{uplink_freq_default:.3f}", disabled=True)

    ul4, ul5, ul6 = st.columns(3, gap="small")
    with ul4:
        uplink_bandwidth = st.number_input(
            "Bandwidth (MHz)",
            min_value=0.0,
            value=36.0,
            format="%.2f",
            key="uplink_bw",
        )
    with ul5:
        uplink_feed_power = st.number_input(
            "Feed Power (W)",
            min_value=0.0,
            value=100.0 if purpose == "VSAT" else 200.0,
            format="%.2f",
            key="uplink_feed_power",
        )
    with ul6:
        uplink_antenna_dia = st.number_input(
            "Antenna Dia (m)",
            min_value=0.0,
            value=8.0,
            format="%.2f",
            key="uplink_ant_dia",
        )

with right_col:
    subhead("Downlink Information")

    use_map_downlink = map_link_row("downlink")
    if use_map_downlink:
        downlink_coord_text = st.text_input(
            "Map Coordinate / Link",
            placeholder="23.710, 90.410 or paste Google Maps link",
            key="downlink_coord_text",
        )
        lat, lon = parse_coordinates(downlink_coord_text)
        if lat is not None and lon is not None:
            st.session_state.downlink_lat = lat
            st.session_state.downlink_long = lon

    dl1, dl2, dl3 = st.columns(3, gap="small")
    with dl1:
        downlink_long = st.number_input(
            "Longitude (°E)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            key="downlink_long",
            placeholder="90.996",
        )
    with dl2:
        downlink_lat = st.number_input(
            "Latitude (°N)",
            min_value=-90.0,
            max_value=90.0,
            format="%.3f",
            key="downlink_lat",
            placeholder="14.580",
        )
    with dl3:
        st.text_input("Downlink Frequency (GHz)", value=f"{downlink_freq_default:.3f}", disabled=True)

    dr1, dr2, dr3 = st.columns([1, 1, 1], gap="small")
    with dr1:
        downlink_antenna_dia = st.number_input(
            "Antenna Dia (m)",
            min_value=0.0,
            value=0.70 if purpose == "VSAT" else 1.80,
            format="%.2f",
            key="downlink_ant_dia",
        )
    with dr2:
        if purpose == "VSAT":
            return_link_feed_power = st.number_input(
                "Return Feed Power (W)",
                min_value=0.0,
                value=20.0,
                format="%.2f",
                key="return_feed_power",
            )
        else:
            return_link_feed_power = None
            st.text_input("Service Type", value="Broadcast", disabled=True)
    with dr3:
        use_lnb = st.checkbox("Use LNB", key="use_lnb")

    if use_lnb:
        lr1, lr2 = st.columns(2, gap="small")
        with lr1:
            fwd_rx_lnb = st.number_input(
                "FWD Rx LNB (W)",
                min_value=0.0,
                value=0.0,
                format="%.2f",
                key="fwd_rx_lnb",
            )
        with lr2:
            if purpose == "VSAT":
                rtn_rx_lnb = st.number_input(
                    "RTN Rx LNB (W)",
                    min_value=0.0,
                    value=0.0,
                    format="%.2f",
                    key="rtn_rx_lnb",
                )
            else:
                rtn_rx_lnb = 0.0
    else:
        fwd_rx_lnb = 0.0
        rtn_rx_lnb = 0.0

# ---------------------------------------------------------
# Coordinates and geometry
# ---------------------------------------------------------
uplink_lon = st.session_state.uplink_long
uplink_lat = st.session_state.uplink_lat
downlink_lon = st.session_state.downlink_long
downlink_lat = st.session_state.downlink_lat

uplink_pos = safe_position(uplink_lat, uplink_lon, satellite_longitude)
downlink_pos = safe_position(downlink_lat, downlink_lon, satellite_longitude)

# ---------------------------------------------------------
# Positioning
# ---------------------------------------------------------
st.markdown('<hr class="compact-hr">', unsafe_allow_html=True)

p1, p2 = st.columns(2, gap="small")
with p1:
    subhead("Uplink Antenna Positioning")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.text_input("Azimuth (°)", value=null_text(uplink_pos["azimuth_deg"]), disabled=True, key="uplink_position_azimuth")
    with c2:
        st.text_input("Elevation (°)", value=null_text(uplink_pos["elevation_deg"]), disabled=True, key="uplink_position_elevation")
    with c3:
        st.text_input("Slant Range (km)", value=null_text(uplink_pos["slant_range_km"]), disabled=True, key="uplink_position_slant_range")

with p2:
    subhead("Downlink Antenna Positioning")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.text_input("Azimuth (°)", value=null_text(downlink_pos["azimuth_deg"]), disabled=True, key="downlink_position_azimuth")
    with c2:
        st.text_input("Elevation (°)", value=null_text(downlink_pos["elevation_deg"]), disabled=True, key="downlink_position_elevation")
    with c3:
        st.text_input("Slant Range (km)", value=null_text(downlink_pos["slant_range_km"]), disabled=True, key="downlink_position_slant_range")

# ---------------------------------------------------------
# Core calculations
# ---------------------------------------------------------
forward_output = {
    "useful_eirp_dbw": None,
    "cni_db": None,
    "modcod": None,
    "expected_datarate_mbps": None,
}
return_output = {
    "useful_eirp_dbw": None,
    "cni_db": None,
    "modcod": None,
    "expected_datarate_mbps": None,
}

try:
    valid_uplink = uplink_lat is not None and uplink_lon is not None and validate_coordinates(uplink_lat, uplink_lon)
    valid_downlink = downlink_lat is not None and downlink_lon is not None and validate_coordinates(downlink_lat, downlink_lon)
    valid_uplink_sr = uplink_pos["slant_range_km"] != ""
    valid_downlink_sr = downlink_pos["slant_range_km"] != ""

    if valid_uplink and valid_downlink and valid_uplink_sr and valid_downlink_sr:
        forward_uplink = LinkInputs(
            frequency_ghz=uplink_freq_default,
            bandwidth_mhz=uplink_bandwidth,
            feed_power_w=uplink_feed_power,
            antenna_diameter_m=uplink_antenna_dia,
            slant_range_km=uplink_pos["slant_range_km"],
            lnb_power_w=0.0,
        )

        forward_downlink = LinkInputs(
            frequency_ghz=downlink_freq_default,
            bandwidth_mhz=uplink_bandwidth,
            feed_power_w=1.0,
            antenna_diameter_m=downlink_antenna_dia,
            slant_range_km=downlink_pos["slant_range_km"],
            lnb_power_w=fwd_rx_lnb or 0.0,
            user_longitude_deg=downlink_lon,
            user_latitude_deg=downlink_lat,
        )

        forward_satellite = SatelliteInputs(
            satellite_eirp_dbw=band_info["defaults"]["best_eirp_dbw"]
        )

        return_uplink = return_downlink = return_satellite = None

        if purpose == "VSAT":
            return_uplink = LinkInputs(
                frequency_ghz=uplink_freq_default,
                bandwidth_mhz=uplink_bandwidth,
                feed_power_w=return_link_feed_power if return_link_feed_power is not None else 0.0,
                antenna_diameter_m=downlink_antenna_dia,
                slant_range_km=downlink_pos["slant_range_km"],
                lnb_power_w=0.0,
                user_longitude_deg=uplink_lon,
                user_latitude_deg=uplink_lat,
            )

            return_downlink = LinkInputs(
                frequency_ghz=downlink_freq_default,
                bandwidth_mhz=uplink_bandwidth,
                feed_power_w=1.0,
                antenna_diameter_m=uplink_antenna_dia,
                slant_range_km=uplink_pos["slant_range_km"],
                lnb_power_w=rtn_rx_lnb or 0.0,
            )

            return_satellite = SatelliteInputs(
                satellite_eirp_dbw=band_info["defaults"]["best_eirp_dbw"]
            )

        link_result = calculate_forward_and_return_for_dashboard(
            band_name=frequency_band,
            forward_uplink=forward_uplink,
            forward_downlink=forward_downlink,
            forward_satellite=forward_satellite,
            return_uplink=return_uplink,
            return_downlink=return_downlink,
            return_satellite=return_satellite,
        )

        modcod_result = calculate_dashboard_modcod_outputs(
            forward_cni_db=link_result["dashboard_output"]["forward_effective_cni_db"],
            forward_bandwidth_mhz=uplink_bandwidth,
            return_cni_db=link_result["dashboard_output"]["return_effective_cni_db"],
            return_bandwidth_mhz=uplink_bandwidth if purpose == "VSAT" else None,
        )

        forward_output = {
            "useful_eirp_dbw": link_result["dashboard_output"]["forward_useful_eirp_dbw"],
            "cni_db": link_result["dashboard_output"]["forward_effective_cni_db"],
            "modcod": modcod_result["dashboard_output"]["forward_modcod"],
            "expected_datarate_mbps": modcod_result["dashboard_output"]["forward_expected_bitrate_mbps"],
        }

        if purpose == "VSAT":
            return_output = {
                "useful_eirp_dbw": link_result["dashboard_output"]["return_useful_eirp_dbw"],
                "cni_db": link_result["dashboard_output"]["return_effective_cni_db"],
                "modcod": modcod_result["dashboard_output"]["return_modcod"],
                "expected_datarate_mbps": modcod_result["dashboard_output"]["return_expected_bitrate_mbps"],
            }

except Exception:
    forward_output = {
        "useful_eirp_dbw": None,
        "cni_db": None,
        "modcod": None,
        "expected_datarate_mbps": None,
    }
    return_output = {
        "useful_eirp_dbw": None,
        "cni_db": None,
        "modcod": None,
        "expected_datarate_mbps": None,
    }

# ---------------------------------------------------------
# Outputs
# ---------------------------------------------------------
st.markdown('<hr class="compact-hr">', unsafe_allow_html=True)

if purpose == "VSAT":
    o1, o2 = st.columns(2, gap="small")
else:
    o1 = st.container()
    o2 = None

with o1:
    subhead("Forward Link Output")
    fo1, fo2, fo3, fo4 = st.columns([1, 1, 1, 1], gap="small")
    with fo1:
        st.text_input("Useful EIRP (dBW)", value=null_text(forward_output["useful_eirp_dbw"]), disabled=True, key="forward_useful_eirp")
    with fo2:
        st.text_input("C/(N+I) (dB)", value=null_text(forward_output["cni_db"]), disabled=True, key="forward_cni")
    with fo3:
        st.text_input("Achievable MODCOD", value=null_text(forward_output["modcod"], 0), disabled=True, key="forward_modcod")
    with fo4:
        st.text_input("Expected Datarate (Mbps)", value=null_text(forward_output["expected_datarate_mbps"]), disabled=True, key="forward_datarate")

if purpose == "VSAT" and o2 is not None:
    with o2:
        subhead("Return Link Output")
        ro1, ro2, ro3, ro4 = st.columns([1, 1, 1, 1], gap="small")
        with ro1:
            st.text_input("Useful EIRP (dBW)", value=null_text(return_output["useful_eirp_dbw"]), disabled=True, key="return_useful_eirp")
        with ro2:
            st.text_input("C/(N+I) (dB)", value=null_text(return_output["cni_db"]), disabled=True, key="return_cni")
        with ro3:
            st.text_input("Achievable MODCOD", value=null_text(return_output["modcod"], 0), disabled=True, key="return_modcod")
        with ro4:
            st.text_input("Expected Datarate (Mbps)", value=null_text(return_output["expected_datarate_mbps"]), disabled=True, key="return_datarate")
