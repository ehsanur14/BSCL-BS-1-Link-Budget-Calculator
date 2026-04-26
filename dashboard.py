# =========================================================
# FILE: dashboard.py
# =========================================================

from pathlib import Path
from html import escape

import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium

from bitrate_modcod_det import calculate_dashboard_modcod_outputs
from calculating_ele_azi import calculate_for_dashboard, validate_coordinates
from fr_sel_preset import BAND_DEFAULTS, BSCL_LOCATIONS, DIVISIONAL_CITY_LOCATIONS, SATELLITE_PRESETS
from fwd_eirp_cn_cal import LinkInputs, SatelliteInputs, calculate_forward_and_return_for_dashboard


st.set_page_config(page_title="Link Budget Calculations (BS-1)", layout="wide", initial_sidebar_state="collapsed")

SATELLITE_NAME = "BS-1"
OUTPUT_KEYS = ("useful_eirp_dbw", "cni_db", "modcod", "expected_datarate_mbps")
POSITION_KEYS = ("azimuth_deg", "elevation_deg", "slant_range_km")
EMPTY_OUTPUT = dict.fromkeys(OUTPUT_KEYS)
EMPTY_POSITION = dict.fromkeys(POSITION_KEYS, "")


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
        uplink_lon = st.number_input(
            "Longitude (deg E)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            step=1.0,
            key="uplink_long",
            disabled=disabled,
        )
    with c2:
        uplink_lat = st.number_input(
            "Latitude (deg N)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            step=1.0,
            key="uplink_lat",
            disabled=disabled,
        )
    with c3:
        st.text_input("Uplink Frequency (GHz)", value=f"{uplink_freq_default:.2f}", disabled=True)

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        bandwidth = st.number_input(
            "Bandwidth (MHz)",
            value=36.0,
            min_value=0.0,
            max_value=36.0,
            format="%.2f",
            step=1.0,
            key="uplink_bw",
        )
    with c2:
        feed_power = st.number_input(
            "Feed Power (W)",
            value=100.0 if purpose == "VSAT" else 200.0,
            format="%.2f",
            step=1.0,
            key="uplink_feed_power",
        )
    with c3:
        antenna_dia = st.number_input("Antenna Dia (m)", value=8.0, format="%.2f", step=1.0, key="uplink_ant_dia")

    return uplink_lon, uplink_lat, bandwidth, feed_power, antenna_dia


def render_downlink_inputs(purpose, downlink_freq_default):
    subhead("Downlink Information")
    read_map_coordinates("downlink")

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        downlink_lon = st.number_input(
            "Longitude (deg E)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            step=1.0,
            key="downlink_long",
        )
    with c2:
        downlink_lat = st.number_input(
            "Latitude (deg N)",
            min_value=-180.0,
            max_value=180.0,
            format="%.3f",
            step=1.0,
            key="downlink_lat",
        )
    with c3:
        st.text_input("Downlink Frequency (GHz)", value=f"{downlink_freq_default:.3f}", disabled=True)

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        antenna_dia = st.number_input(
            "Antenna Dia (m)",
            value=0.70 if purpose == "VSAT" else 1.80,
            format="%.2f",
            step=1.0,
            key="downlink_ant_dia",
        )
    with c2:
        return_feed_power = (
            st.number_input("Return Feed Power (W)", value=20.0, format="%.2f", step=1.0, key="return_feed_power")
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


def calculate_button(key="calculate_link_budget"):
    st.markdown('<div style="height:.35rem"></div>', unsafe_allow_html=True)
    return st.button("Calculate", key=key, use_container_width=True)


def render_position(title, position, prefix):
    open_stat_panel(title)
    labels = ("Azimuth (deg)", "Elevation (deg)")
    open_stat_grid()
    cols = st.columns(2, gap="small")
    for col, label, key in zip(cols, labels, POSITION_KEYS[:2]):
        with col:
            readonly_value(label, null_text(position[key]))
    close_div()
    close_div()


def readonly_value(label, value):
    safe_label = escape(str(label))
    safe_value = escape(str(value))
    st.markdown(
        f"""
        <div class="readonly-field">
            <div class="readonly-label">{safe_label}</div>
            <div class="readonly-value">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_output(title, output, prefix):
    open_stat_panel(title)
    labels = ("Useful EIRP (dBW)", "C/(N+I) (dB)", "Achievable MODCOD", "Expected Datarate (Mbps)")
    nds = (2, 2, 0, 2)
    top_cols = st.columns(2, gap="small")
    bottom_cols = st.columns(2, gap="small")
    cols = [top_cols[0], top_cols[1], bottom_cols[0], bottom_cols[1]]
    for col, label, key, nd in zip(cols, labels, OUTPUT_KEYS, nds):
        with col:
            readonly_value(label, null_text(output[key], nd))
    close_div()


def has_negative_elevation(*positions):
    for position in positions:
        try:
            if position.get("elevation_deg") not in ("", None) and float(position["elevation_deg"]) < 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def has_low_power_result(*outputs):
    for output in outputs:
        if not output:
            continue
        if output.get("useful_eirp_dbw") in ("", None) or output.get("cni_db") in ("", None) or output.get("modcod") in ("", None):
            return True
    return False


def has_any_result(*outputs):
    for output in outputs:
        if output and any(output.get(key) not in ("", None) for key in OUTPUT_KEYS):
            return True
    return False


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
    if modcod[f"{direction}_modcod"] in ("", None):
        return EMPTY_OUTPUT.copy()
    return {
        "useful_eirp_dbw": dashboard[f"{direction}_useful_eirp_dbw"],
        "cni_db": dashboard[f"{direction}_effective_cni_db"],
        "modcod": modcod[f"{direction}_modcod"],
        "expected_datarate_mbps": modcod[f"{direction}_expected_bitrate_mbps"],
    }


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
                inputs["uplink_lon"],
                inputs["uplink_lat"],
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
header[data-testid="stHeader"],
[data-testid="collapsedControl"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer{display:none!important;}
.block-container{max-width:1920px;padding-top:.18rem;padding-bottom:.18rem;padding-left:.9rem;padding-right:.9rem;}
.stMarkdown p, div[data-testid="stVerticalBlock"] > div{margin-bottom:.04rem;}
.hero-shell{
    background:transparent;
    border:none;
    border-radius:0;
    box-shadow:none;
    padding:0;
    margin:-.25rem 0 .2rem 0;
}
.hero-shell [data-testid="stImage"]{
    margin:0!important;
}
.hero-shell [data-testid="stImage"] img{
    display:block;
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
    border-radius:0;
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
    border-radius:0;
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
    border-radius:0;
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
    border-radius:0;
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
    border-radius:0;
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
    border-radius:0;
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
    border-radius:0!important;
    min-height:2.42rem!important;
    border:1px solid #dfe5ee!important;
    box-shadow:none!important;
    background:#fff!important;
    font-size:.92rem!important;
}
div[data-testid="stSelectbox"],
div[data-testid="stSelectbox"] *,
div[data-baseweb="select"],
div[data-baseweb="select"] *,
ul[role="listbox"],
ul[role="listbox"] *{
    border-radius:0!important;
}
div[data-testid="stTextInput"] input[disabled],
div[data-testid="stNumberInput"] input[disabled]{
    background-color:var(--input)!important;
    color:#27384f!important;
    -webkit-text-fill-color:#27384f!important;
    opacity:1!important;
    font-weight:800!important;
}
.readonly-field{
    margin:0 0 .45rem 0;
}
.readonly-label{
    font-size:.76rem;
    font-weight:700;
    color:#3d4c62;
    margin:0 0 .18rem 0;
}
.readonly-value{
    min-height:2.42rem;
    display:flex;
    align-items:center;
    border:1px solid #dfe5ee;
    border-radius:0;
    background:var(--input);
    color:#27384f;
    font-size:.92rem;
    font-weight:800;
    padding:.42rem .8rem;
}
.nb-note{
    display:inline-flex;
    align-items:center;
    border:1px solid #efc7c7;
    border-radius:0;
    background:#fff2f2;
    color:#8b2c2c;
    font-size:.78rem;
    font-weight:800;
    padding:.32rem .58rem;
    margin:.16rem 0 .35rem 0;
}
.best-case-note{
    color:#5a6b81;
    font-size:.78rem;
    font-weight:700;
    margin:.22rem 0 .1rem 0;
}
div[data-testid="stCheckbox"]{padding-top:.18rem;}
div[data-testid="stRadio"] label{font-weight:700!important;}
div[data-testid="stButton"] > button{
    min-height:2.45rem;
    border-radius:0;
    border:1px solid #2f6da6;
    background:linear-gradient(180deg, #2d78ba 0%, #235f99 100%);
    color:#fff;
    font-weight:800;
    font-size:.9rem;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stButton"] > button:focus,
div[data-testid="stButton"] > button:active{
    border-color:#2d8a43!important;
    background:#dff4e4!important;
    color:#14351f!important;
    box-shadow:0 0 0 1px rgba(45,138,67,.18)!important;
}
div[data-testid="stButton"] > button[kind="secondary"]{
    background:#fff;
    color:#294869;
}
.map-control-row div[data-testid="stButton"] > button{
    min-height:2rem!important;
    padding:.18rem .8rem!important;
    border-radius:0!important;
    font-size:.78rem!important;
}
.map-control-row div[data-testid="stSelectbox"] > div{
    min-height:2rem!important;
    border-radius:0!important;
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
    "stored_forward_output": EMPTY_OUTPUT.copy(),
    "stored_return_output": EMPTY_OUTPUT.copy(),
    "stored_debug_payload": {},
    "stored_inputs": None,
})

satellite_longitude = SATELLITE_PRESETS[SATELLITE_NAME]["orbital_longitude_deg"]

active_map_picker = st.session_state.get("active_map_picker")
if active_map_picker in {"uplink", "downlink"}:
    render_map_picker_screen(active_map_picker)
    st.stop()

render_header()
main_left, main_right = st.columns([1.28, 1.0], gap="large")
with main_left:
    open_panel()
    panel_title("Calculation Inputs")
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
    calculate_clicked = calculate_button()
    close_panel()

uplink_lon = float(uplink_lon)
uplink_lat = float(uplink_lat)
downlink_lon = float(downlink_lon)
downlink_lat = float(downlink_lat)

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
}

uplink_pos = safe_position(uplink_lat, uplink_lon, satellite_longitude)
downlink_pos = safe_position(downlink_lat, downlink_lon, satellite_longitude)

if calculate_clicked or st.session_state.stored_inputs is None:
    calc_inputs = {
        **current_inputs,
        "uplink_pos": uplink_pos,
        "downlink_pos": downlink_pos,
    }
    forward_output, return_output, debug_payload = calculate_outputs(calc_inputs)
    st.session_state.stored_forward_output = forward_output
    st.session_state.stored_return_output = return_output
    st.session_state.stored_debug_payload = debug_payload
    st.session_state.stored_inputs = current_inputs.copy()

inputs_are_current = st.session_state.stored_inputs == current_inputs
forward_output = st.session_state.stored_forward_output if inputs_are_current else EMPTY_OUTPUT.copy()
return_output = st.session_state.stored_return_output if inputs_are_current else EMPTY_OUTPUT.copy()
debug_payload = st.session_state.stored_debug_payload

if not validate_coordinates(uplink_lat, uplink_lon):
    st.warning("Uplink latitude/longitude -180 to 180 range er moddhe dite hobe. Shothik position din.")
if not validate_coordinates(downlink_lat, downlink_lon):
    st.warning("Downlink latitude/longitude -180 to 180 range er moddhe dite hobe. Shothik position din.")

with main_right:
    open_panel()
    panel_title("Outputs", "Calculated" if inputs_are_current else "Click Calculate")
    section_bar("Antenna Positioning")
    if has_negative_elevation(uplink_pos, downlink_pos):
        st.markdown('<div class="nb-note">NB: satellite coverage nai</div>', unsafe_allow_html=True)
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
    if inputs_are_current and has_low_power_result(forward_output, return_output):
        st.markdown('<div class="nb-note">NB: Insufficient transmit power. Please increase the transmission power.</div>', unsafe_allow_html=True)
    if inputs_are_current and has_any_result(forward_output, return_output):
        st.markdown('<div class="best-case-note">The result is calculated for the best case scenario.</div>', unsafe_allow_html=True)
    close_panel()
