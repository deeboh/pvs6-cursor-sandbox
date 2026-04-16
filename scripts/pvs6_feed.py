from datetime import datetime, timezone
import os
import re
from urllib.parse import urljoin

import requests
from flask import Flask, jsonify

app = Flask(__name__)

BASE_URL = os.getenv("PVS6_MONITORING_URL", "http://localhost:5173/")
TELEMETRY_URL = os.getenv("PVS6_MONITORING_TELEMETRY_URL", "").strip()
TELEMETRY_PATH = os.getenv("PVS6_MONITORING_TELEMETRY_PATH", "/api/telemetry/today")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("PVS6_MONITORING_TIMEOUT", "8"))
ALLOW_FALLBACK_SAMPLE = (
    os.getenv("PVS6_ALLOW_FALLBACK_SAMPLE")
    or os.getenv("PVS6_ALLOW_FALLBACK_MOCK", "0")
) == "1"
DASHBOARD_URL = os.getenv("STAGING_DASHBOARD_URL", "https://staging.example.com/pvs6")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_string(value):
    if value is None:
        return None
    return str(value)


def _find_first(payload, keys):
    wanted = {k.lower() for k in keys}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in wanted and value is not None:
                return value
        for value in payload.values():
            found = _find_first(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first(item, keys)
            if found is not None:
                return found
    return None


def _normalize_telemetry(raw):
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict) and raw["data"].get("devices") is not None:
        return _normalize_proxy_all_payload(raw)

    timestamp = _coerce_string(_find_first(raw, {"timestamp", "ts", "datetime"})) or utc_now_iso()
    site = _coerce_string(_find_first(raw, {"site", "site_name", "system_name", "name"})) or "PVS6 Site"
    energy_kwh_today = _coerce_float(_find_first(raw, {"energy_kwh_today", "energy_today_kwh", "daily_kwh", "kwh_today"}))
    peak_power_kw = _coerce_float(_find_first(raw, {"peak_power_kw", "peak_kw", "max_power_kw", "power_peak_kw"}))
    inverter_status = _coerce_string(_find_first(raw, {"inverter_status", "status", "inverter"})) or "unknown"
    uptime_percent = _coerce_float(_find_first(raw, {"uptime_percent", "uptime_pct", "uptime"}))
    weather_summary = _coerce_string(_find_first(raw, {"weather_summary", "weather", "conditions"})) or "not provided"
    co2_offset_kg = _coerce_float(_find_first(raw, {"co2_offset_kg", "co2_kg", "carbon_offset_kg"}))
    dashboard_url = _coerce_string(_find_first(raw, {"dashboard_url", "dashboard", "url"})) or DASHBOARD_URL

    return {
        "timestamp": timestamp,
        "site": site,
        "energy_kwh_today": energy_kwh_today,
        "peak_power_kw": peak_power_kw,
        "inverter_status": inverter_status,
        "uptime_percent": uptime_percent,
        "weather_summary": weather_summary,
        "co2_offset_kg": co2_offset_kg,
        "dashboard_url": dashboard_url,
    }


def _normalize_proxy_all_payload(raw):
    data = raw.get("data", raw)
    devices = data.get("devices") or []
    if isinstance(devices, dict):
        devices = devices.get("devices") or []
    if not isinstance(devices, list):
        devices = []

    site_profile = data.get("site_profile") or {}
    if not isinstance(site_profile, dict):
        site_profile = {}

    inverters = [d for d in devices if isinstance(d, dict) and d.get("DEVICE_TYPE") == "Inverter"]
    prod_meter = next(
        (d for d in devices if isinstance(d, dict) and d.get("subtype") == "GROSS_PRODUCTION_SITE"),
        None,
    )
    current_kw = _coerce_float((prod_meter or {}).get("p_3phsum_kw"))
    if current_kw is None:
        current_kw = _coerce_float(sum(_coerce_float(i.get("p_3phsum_kw")) or 0.0 for i in inverters))

    any_working = any((i.get("STATE") or "").lower() == "working" for i in inverters if isinstance(i, dict))
    inverter_status = "online" if any_working or (current_kw and current_kw > 0.01) else ("offline" if inverters else "unknown")

    return {
        "timestamp": utc_now_iso(),
        "site": site_profile.get("site_name") or site_profile.get("pvs_serial") or "PVS6 Site",
        "energy_kwh_today": _coerce_float(_find_first(data, {"energy_kwh_today", "daily_kwh", "kwh_today"})),
        "peak_power_kw": current_kw,
        "inverter_status": inverter_status,
        "uptime_percent": _coerce_float(_find_first(data, {"uptime_percent", "uptime_pct", "uptime"})),
        "weather_summary": _coerce_string(_find_first(data, {"weather_summary", "weather", "conditions"})) or "not provided",
        "co2_offset_kg": _coerce_float(_find_first(data, {"co2_offset_kg", "co2_kg", "carbon_offset_kg"})),
        "dashboard_url": DASHBOARD_URL,
    }


def _discover_proxy_telemetry_url():
    try:
        config_url = urljoin(BASE_URL, "/src/config.js")
        response = requests.get(config_url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        match = re.search(r'PROXY_BASE\s*=\s*["\']([^"\']+)["\']', response.text)
        if not match:
            return None
        proxy_base = match.group(1).strip()
        return urljoin(proxy_base if proxy_base.endswith("/") else f"{proxy_base}/", "all")
    except Exception:
        return None


def _candidate_urls():
    urls = []
    if TELEMETRY_URL:
        urls.append(TELEMETRY_URL)
    else:
        urls.extend(
            [
                urljoin(BASE_URL, TELEMETRY_PATH),
                urljoin(BASE_URL, "/telemetry/today"),
                urljoin(BASE_URL, "/data/telemetry/today"),
            ]
        )
    discovered_proxy_url = _discover_proxy_telemetry_url()
    if discovered_proxy_url:
        urls.append(discovered_proxy_url)
    return list(dict.fromkeys(urls))


def _fetch_remote_json():
    errors = []
    for url in _candidate_urls():
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            return payload, url, errors
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("; ".join(errors))


def _fallback_payload():
    return {
        "timestamp": utc_now_iso(),
        "site": "PVS6 Sandbox Site (fallback)",
        "energy_kwh_today": 31.8,
        "peak_power_kw": 5.4,
        "inverter_status": "online",
        "uptime_percent": 99.7,
        "weather_summary": "clear morning, light clouds afternoon",
        "co2_offset_kg": 12.9,
        "dashboard_url": DASHBOARD_URL,
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "pvs6-feed",
        "source_base_url": BASE_URL,
        "source_telemetry_url": TELEMETRY_URL or urljoin(BASE_URL, TELEMETRY_PATH),
        "fallback_sample_enabled": ALLOW_FALLBACK_SAMPLE,
    }


@app.get("/telemetry/today")
def telemetry_today():
    try:
        raw, source_url, fetch_errors = _fetch_remote_json()
        normalized = _normalize_telemetry(raw)
        normalized["source_url"] = source_url
        if fetch_errors:
            normalized["source_warnings"] = fetch_errors
        return jsonify(normalized)
    except Exception as exc:
        if ALLOW_FALLBACK_SAMPLE:
            fallback = _fallback_payload()
            fallback["source_warning"] = f"Remote fetch failed, using fallback: {exc}"
            return jsonify(fallback)
        return jsonify(
            {
                "error": "failed_to_fetch_pvs6_source",
                "message": str(exc),
                "checked_urls": _candidate_urls(),
            }
        ), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4020)
