"""Multi-Site Victron VRM Monitoring Automation
Automatically monitors ALL sites (20+ scalable) and generates per-site reports.
Loops through all sites in DEFAULT_SITES and generates dashboards, CSVs, and anomaly alerts.
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import sys
import time as time_mod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
logger = logging.getLogger(__name__)

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
BASE_URL = "https://vrmapi.victronenergy.com/v2"
DATE_INPUT_FMT = "%Y-%m-%d, %H:%M"
DATETIME_FMT = "%Y-%m-%d %H:%M"
NUM_MPPTS = 6
NOMINAL_VOLTAGE = 230

MPPT_ATTR_MAP = {
    "695": "PV Volt MPPT{n} [V]",
    "696": "PV Volt MPPT{n}.1",
    "697": "PV Volt MPPT{n}.2",
    "698": "PV Volt MPPT{n}.3",
    "87":  "PV Curr MPPT{n} [A]",
    "442": "PV Pow MPPT{n} [W]",
    "81":  "Btty Volt MPPT{n} [V]",
    "82":  "Btty Curr MPPT{n} [A]",
    "107": "Btty Watts MPPT{n} [W]",
}

ENDPOINTS = {
    "mppt": {"codes": ["PVV0","PVV1","PVV2","PVV3","PVI","PVP","ScV","ScI","ScW"], "instance": 279},
    "inverter": {"codes": ["CV","CI","OV1","OI1","OP1","OV2","OI2","OP2","OV3","OI3","OP3","OF","t9"], "instance": 276, "extra": "useMinMax=1"},
    "battery": {"codes": ["SOC","V","I","H11"], "instance": 512, "extra": "interval=15mins"},
}

# ALL SITES - Add more here anytime, loop handles all automatically
DEFAULT_SITES = {
    "Mamarongo":     {"id": 140117, "mppt_w": 4000,  "inv_kva": 5000,  "batt_kwh": 21312},
    "Coqui Trek":    {"id": 154700, "mppt_w": 5800,  "inv_kva": 3000,  "batt_kwh": 14400},
    "Coqui Impact":  {"id": 154724, "mppt_w": 3440,  "inv_kva": 6000,  "batt_kwh": 39072},
    "Trapiche":      {"id": 192342, "mppt_w": 4000,  "inv_kva": 3000,  "batt_kwh": 3552},
    "Juanchaco":     {"id": 195216, "mppt_w": 11500, "inv_kva": 9000,  "batt_kwh": 21312},
    "Munduruku":     {"id": 273142, "mppt_w": 4900,  "inv_kva": 3000,  "batt_kwh": 14400},
    "OPC Control":   {"id": 304591, "mppt_w": 11500, "inv_kva": 24000, "batt_kwh": 120000},
    "OPC Kamok":     {"id": 320393, "mppt_w": 11500, "inv_kva": 48000, "batt_kwh": 260000},
    "OPC Morani":    {"id": 307120, "mppt_w": 4900,  "inv_kva": 3000,  "batt_kwh": 60000},
    "Borana Hq":     {"id": 304791, "mppt_w": 11500, "inv_kva": 45000, "batt_kwh": 200000},
    "Maison Dorcas": {"id": 409822, "mppt_w": 5800,  "inv_kva": 45000, "batt_kwh": 30000},
    "Kabula":        {"id": 933617, "mppt_w": 11500, "inv_kva": 10000, "batt_kwh": 20000},
    "Ukala AIC":     {"id": 815230, "mppt_w": 11500, "inv_kva": 10000, "batt_kwh": 20000},
}

# ─── API LAYER ───────────────────────────────────────────────────────────────
def create_session(token: str) -> requests.Session:
    """Create authenticated session with retry logic"""
    session = requests.Session()
    session.headers["X-Authorization"] = f"Token {token}"
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5))
    return session

def fetch(session: requests.Session, url: str, cache_dir: Path | None = None, cache_ttl: float = 1.0) -> dict:
    """Fetch data with caching"""
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.json"
        if cache_file.exists():
            age_hours = (time_mod.time() - cache_file.stat().st_mtime) / 3600
            if age_hours < cache_ttl:
                with open(cache_file) as f:
                    return json.load(f)

    response = session.get(url)
    response.raise_for_status()
    data = response.json()

    if cache_dir:
        with open(cache_file, "w") as f:
            json.dump(data, f)

    return data

def fetch_all(session: requests.Session, site_id: str, start: float, end: float, cache_dir: Path | None, cache_ttl: float) -> dict:
    """Fetch all data in parallel"""
    base = f"{BASE_URL}/installations/{site_id}"
    urls = {}

    for name, ep in ENDPOINTS.items():
        params = "&".join(f"attributeCodes[]={c}" for c in ep["codes"])
        url = f"{base}/widgets/Graph?{params}&instance={ep['instance']}&start={start}&end={end}"
        if "extra" in ep:
            url += f"&{ep['extra']}"
        urls[name] = url

    urls["energy"] = f"{base}/stats?type=kwh&start={start}&end={end}&interval=days"
    urls["attributes"] = f"{base}/attributes"

    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, session, url, cache_dir, cache_ttl): name for name, url in urls.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch {name}: {e}")
                return None

    for name in ENDPOINTS:
        results[name] = results[name]["records"]["data"]

    return results

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────
def to_unix(date_str: str) -> float:
    return datetime.datetime.strptime(date_str, DATE_INPUT_FMT).timestamp()

def to_dates(records: dict, key: str) -> list[str]:
    return [datetime.datetime.fromtimestamp(int(row[0])).strftime(DATETIME_FMT) for row in records[key]]

def col_values(records: dict, key: str) -> list:
    return [row[1] for row in records[key]]

def col_minmax(records: dict, key: str) -> list:
    return [row[3] if len(row) > 3 else row[1] for row in records[key]]

def compute_intervals(dates: pd.Series) -> pd.Series:
    dt = pd.to_datetime(dates, format=DATETIME_FMT)
    intervals = dt.diff().dt.total_seconds() / 3600
    intervals.iloc[0] = intervals.iloc[1]
    return intervals

def init_dataframe(records: dict, date_key: str, columns: list[str]) -> tuple[pd.DataFrame, int]:
    data_len = len(records[date_key])
    df = pd.DataFrame(np.zeros((data_len, len(columns))), columns=columns)
    df["Date"] = to_dates(records, date_key)
    df["Time Interval"] = compute_intervals(df["Date"])
    return df, data_len

def apply_timezone(df: pd.DataFrame, offset: datetime.timedelta) -> pd.DataFrame:
    df["Date"] = pd.to_datetime(df["Date"]) + offset
    return df

def safe_efficiency(prod_in: pd.Series, prod_out: pd.Series) -> float:
    total_in = prod_in.sum()
    return round((1 - (total_in - prod_out.sum()) / total_in) * 100, 1) if total_in > 0 else np.nan

def avg_nonzero(series: pd.Series) -> float:
    nonzero = series[series != 0]
    return round(nonzero.mean(), 1) if len(nonzero) > 0 else np.nan

def validate_response(data: dict, required_keys: list[str], label: str) -> None:
    missing = [k for k in required_keys if k not in data]
    if missing:
        logger.error(f"{label} response missing keys: {missing}")
        return False
    empty = [k for k in required_keys if len(data[k]) == 0]
    if empty:
        logger.warning(f"{label} has empty data for keys: {empty}")
    return True

# ─── PROCESSING FUNCTIONS ────────────────────────────────────────────────────
def process_mppts(mppt_responses: list[dict], mppt_size_w: int, timezone: datetime.timedelta) -> tuple[pd.DataFrame, dict]:
    """Process MPPT data"""
    data = mppt_responses[0]
    validate_response(data, list(MPPT_ATTR_MAP.keys()), "MPPT")

    if len(data["442"]) == 0:
        logger.error("No MPPT data for this period")
        return None, None

    columns = ["Date", "Time Interval", "Installation"]
    for n in range(1, NUM_MPPTS + 1):
        columns.extend([
            f"PV Volt MPPT{n} [V]", f"PV Volt MPPT{n}.1", f"PV Volt MPPT{n}.2", f"PV Volt MPPT{n}.3",
            f"PV Curr MPPT{n} [A]", f"PV Pow MPPT{n} [W]",
            f"Btty Volt MPPT{n} [V]", f"Btty Curr MPPT{n} [A]", f"Btty Watts MPPT{n} [W]",
            f"ProductionIn {n} [Wh]", f"ProductionOut {n} [Wh]", f"Eff {n} [%]",
        ])
    columns.extend(["Total productionIn [Wh]", "Total productionOut [Wh]"])

    df, data_len = init_dataframe(data, "442", columns)
    logger.info(f"MPPT data points: {data_len}")

    for j, mppt_data in enumerate([data], start=1):
        for code, template in MPPT_ATTR_MAP.items():
            if mppt_data.get(code):
                df[template.format(n=j)] = col_values(mppt_data, code)

    total_in = pd.Series(0.0, index=df.index)
    total_out = pd.Series(0.0, index=df.index)

    for n in range(1, NUM_MPPTS + 1):
        p_in = df[f"PV Pow MPPT{n} [W]"] * df["Time Interval"]
        p_out = df[f"Btty Watts MPPT{n} [W]"] * df["Time Interval"]
        df[f"ProductionIn {n} [Wh]"], df[f"ProductionOut {n} [Wh]"] = p_in, p_out
        df[f"Eff {n} [%]"] = ((1 - (p_in - p_out) / p_in) * 100).replace([np.inf, -np.inf], np.nan)
        total_in += p_in
        total_out += p_out

    df["Total productionIn [Wh]"] = total_in
    df["Total productionOut [Wh]"] = total_out

    stats = {}
    for n in range(1, NUM_MPPTS + 1):
        load_pct = df[f"PV Pow MPPT{n} [W]"] / mppt_size_w * 100
        stats[n] = {
            "pv_vmax": round(df[f"PV Volt MPPT{n} [V]"].max(), 1),
            "efficiency": safe_efficiency(df[f"ProductionIn {n} [Wh]"], df[f"ProductionOut {n} [Wh]"]),
            "load_avg": avg_nonzero(load_pct),
            "load_max": round(load_pct.max(), 1),
            "production_kwh": round(df[f"ProductionOut {n} [Wh]"].sum() / 1000, 1),
        }

    return apply_timezone(df, timezone), stats

def process_inverter(inv_data: dict, inverter_kva: int, timezone: datetime.timedelta) -> tuple[pd.DataFrame, dict]:
    """Process inverter data"""
    validate_response(inv_data, ["32", "33", "26"], "Inverter")

    columns = ["Date", "Installation", "Time Interval", "Voltage [V]", "Current [A]",
               "Input DC Power [W]", "EnergyIn [Wh]", "Frequency [Hz]", "PF",
               "Total ActivePower [W]", "Total ReactivePower [Var]", "Total ApparentPower [VA]",
               "Total energy com [Wh]", "Total energy com+PVAC [Wh]"]
    for p in range(1, 4):
        columns.extend([f"Output Voltage {p} [V]", f"Output Current {p} [A]", f"Output Power {p} [W]",
                       f"Output VA {p} [VA]", f"Energy {p} [Wh]", f"InverterLoad {p}"])

    df, data_len = init_dataframe(inv_data, "32", columns)
    logger.info(f"Inverter data points: {data_len}")

    df["Voltage [V]"] = col_values(inv_data, "32")
    df["Current [A]"] = col_values(inv_data, "33")

    minmax_map = {"20": "Output Voltage 1 [V]", "21": "Output Voltage 2 [V]", "22": "Output Voltage 3 [V]",
                  "23": "Output Current 1 [A]", "24": "Output Current 2 [A]", "25": "Output Current 3 [A]", "26": "Frequency [Hz]"}
    for code, col in minmax_map.items():
        if inv_data.get(code):
            df[col] = col_minmax(inv_data, code)

    for code, col in {"29": "Output Power 1 [W]", "30": "Output Power 2 [W]", "31": "Output Power 3 [W]"}.items():
        if inv_data.get(code):
            df[col] = col_values(inv_data, code)

    df["Input DC Power [W]"] = df["Voltage [V]"] * -df["Current [A]"]
    df["EnergyIn [Wh]"] = df["Input DC Power [W]"] * df["Time Interval"]

    for p in range(1, 4):
        df[f"Output VA {p} [VA]"] = df[f"Output Voltage {p} [V]"] * df[f"Output Current {p} [A]"]
        df[f"Energy {p} [Wh]"] = df[f"Output Power {p} [W]"] * df["Time Interval"]

    df["Total ActivePower [W]"] = sum(df[f"Output Power {p} [W]"] for p in range(1, 4))
    df["Total ApparentPower [VA]"] = sum(df[f"Output VA {p} [VA]"] for p in range(1, 4))
    df["Total energy com [Wh]"] = sum(df[f"Energy {p} [Wh]"] for p in range(1, 4))
    df["PF"] = (df["Total ActivePower [W]"] / df["Total ApparentPower [VA]"]).replace([np.inf, -np.inf], np.nan)

    energy_pos = df["Total energy com [Wh]"][df["Total energy com [Wh]"] > 0].sum()
    energy_in_pos = df["EnergyIn [Wh]"][df["EnergyIn [Wh]"] > 0].sum()

    stats = {
        "avg_hz": round(df["Frequency [Hz]"].mean(skipna=True), 1),
        "efficiency": round((energy_pos / energy_in_pos) * 100, 1) if energy_in_pos > 0 else 0,
        "avg_pf": round(df["PF"][df["Total ActivePower [W]"] > inverter_kva * 0.05].mean(skipna=True), 3),
        "total_load_avg": round(df["Total ApparentPower [VA]"].replace(0, np.nan).mean(skipna=True) / inverter_kva * 100, 1),
        "total_load_max": round(df["Total ApparentPower [VA]"].max() / inverter_kva * 100, 1),
    }

    for p in range(1, 4):
        va = df[f"Output VA {p} [VA]"]
        stats[f"avg_volt_{p}"] = round(df[f"Output Voltage {p} [V]"].replace(0, np.nan).mean(skipna=True), 1)
        stats[f"load_avg_{p}"] = round(va.replace(0, np.nan).mean(skipna=True) / (inverter_kva / 3) * 100, 1)
        stats[f"load_max_{p}"] = round(va.max() / (inverter_kva / 3) * 100, 1)

    return apply_timezone(df, timezone), stats

def process_battery(batt_data: dict, battery_kwh: int, timezone: datetime.timedelta) -> tuple[pd.DataFrame, dict]:
    """Process battery data"""
    validate_response(batt_data, ["51", "47", "49"], "Battery")

    columns = ["Date", "Time Interval", "SOC [%]", "Battery Voltage [V]", "Battery Current [A]", "Battery Watts [W]", "Energy [Wh]"]
    df, data_len = init_dataframe(batt_data, "51", columns)
    logger.info(f"Battery data points: {data_len}")

    for code, col in {"51": "SOC [%]", "47": "Battery Voltage [V]", "49": "Battery Current [A]"}.items():
        df[col] = col_values(batt_data, code)

    df["Battery Watts [W]"] = df["Battery Voltage [V]"] * df["Battery Current [A]"]
    df["Energy [Wh]"] = df["Battery Watts [W]"] * df["Time Interval"]

    soc = df["SOC [%]"]
    stats = {
        "avg_soc": round(soc.mean(), 1),
        "min_soc": round(soc.min(skipna=True), 1),
        "efficiency": round(100 - abs((soc.iloc[-2] - soc.iloc[1]) - (df["Energy [Wh]"].sum() / battery_kwh * 100)), 2),
    }
    return apply_timezone(df, timezone), stats

def check_anomalies(mppt_stats: dict, inv_stats: dict, batt_stats: dict) -> list[str]:
    """Detect anomalies"""
    warnings = []

    for n in range(1, NUM_MPPTS + 1):
        s = mppt_stats[n]
        if s["load_max"] > 100:
            warnings.append(f"MPPT {n} peak load reached {s['load_max']}% (overload)")
        eff = s["efficiency"]
        if isinstance(eff, float) and not np.isnan(eff) and eff < 85:
            warnings.append(f"MPPT {n} efficiency is low at {eff}%")

    for p in range(1, 4):
        if inv_stats.get(f"load_max_{p}", 0) > 100:
            warnings.append(f"Inverter Phase {p} peak load reached {inv_stats[f'load_max_{p}']}% (overload)")
        avg_v = inv_stats.get(f"avg_volt_{p}")
        if isinstance(avg_v, float) and not np.isnan(avg_v) and avg_v > 0:
            deviation = abs(avg_v - NOMINAL_VOLTAGE) / NOMINAL_VOLTAGE * 100
            if deviation > 10:
                warnings.append(f"Phase {p} avg voltage {avg_v}V deviates {deviation:.1f}% from {NOMINAL_VOLTAGE}V nominal")

    if inv_stats["efficiency"] < 80:
        warnings.append(f"Inverter efficiency is low at {inv_stats['efficiency']}%")

    if batt_stats["min_soc"] < 20:
        warnings.append(f"Battery SOC dropped to {batt_stats['min_soc']}% (critically low)")

    if batt_stats["efficiency"] < 50:
        warnings.append(f"Battery efficiency is unusually low at {batt_stats['efficiency']}%")

    return warnings

def generate_charts(df_chart: pd.DataFrame, site_name: str, date_range: str, output_dir: Path) -> None:
    """Generate charts"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True)

    for series, color, label in [
        (df_chart["Production [Wh]"].dropna() / 1000, "#f59e0b", "Solar Production"),
        (df_chart["Consumption cover by Victron [Wh]"].dropna() / 1000, "#3b82f6", "Consumption"),
    ]:
        ax1.plot(series.index, series.values, color=color, linewidth=0.8, label=label, alpha=0.9)
        ax1.fill_between(series.index, series.values, alpha=0.2, color=color)

    ax1.set_ylabel("Energy [kWh]")
    ax1.set_title(f"{site_name} — Hourly Energy Production vs Consumption")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)

    avg_soc = df_chart["Avg SOC [%]"].dropna()
    min_soc = df_chart["Min SOC [%]"].dropna()
    max_soc = df_chart["Max SOC [%]"].dropna()

    common_idx = avg_soc.index.intersection(min_soc.index).intersection(max_soc.index)
    ax2.fill_between(common_idx, min_soc.loc[common_idx], max_soc.loc[common_idx], alpha=0.25, color="#10b981", label="SOC Range")
    ax2.plot(avg_soc.index, avg_soc.values, color="#10b981", linewidth=0.8, label="Avg SOC")
    ax2.axhline(y=20, color="#ef4444", linestyle="--", linewidth=0.8, alpha=0.7, label="Low SOC Threshold")

    ax2.set(ylabel="SOC [%]", xlabel="Date", ylim=(0, 105))
    ax2.set_title(f"{site_name} — Battery State of Charge")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    chart_path = output_dir / f"{site_name}_chart_{date_range}.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Chart saved to {chart_path}")

def print_report(mppt_stats: dict, inv_stats: dict, batt_stats: dict, site_name: str, start: str, end: str) -> None:
    """Print monitoring report"""
    print(f"\n{'='*80}")
    print(f"Monitoring report {site_name} from {start} to {end}")
    print(f"{'='*80}")

    print("------------MPPTs Results----------------------------------------------")
    vmax_parts = []
    for n in range(1, NUM_MPPTS + 1):
        s = mppt_stats[n]
        if n == 1:
            vmax_parts.append(f"Max. PV Voltage 1 [V]= {s['pv_vmax']} (T1) / "
                              f"{s.get('pv_vmax_t2', 0.0)} (T2) / {s.get('pv_vmax_t3', 0.0)} (T3) / "
                              f"{s.get('pv_vmax_t4', 0.0)} (T4)")
        else:
            vmax_parts.append(f"Max. PV Voltage {n} [V]= {s['pv_vmax']}")
    print("   ".join(vmax_parts))

    print(" ".join(f"Production {n} [kWh]= {mppt_stats[n]['production_kwh']}" for n in range(1, NUM_MPPTS + 1)))
    print("  ".join(f"Avg. Efficiency {n} [%]= {mppt_stats[n]['efficiency']}" for n in range(1, NUM_MPPTS + 1)))
    print("  ".join(f"Avg/Max Load {n} [%]= {mppt_stats[n]['load_avg']}/{mppt_stats[n]['load_max']}" for n in range(1, NUM_MPPTS + 1)))

    print("--------------------------Inverters Results--------------------------------")
    print("  ".join(f"Avg Voltage {p} [V] ={inv_stats[f'avg_volt_{p}']}" for p in range(1, 4)))
    print(f"Avg_Hz={inv_stats['avg_hz']}")
    print(f"Avg Efficiency [%]= {inv_stats['efficiency']}")
    print(f"Avg/Max total kVA [%] = {inv_stats['total_load_avg']}/{inv_stats['total_load_max']}"
          + "".join(f" Phase {p}= {inv_stats[f'load_avg_{p}']}/{inv_stats[f'load_max_{p}']}" for p in range(1, 4)))
    print(f"AvgPF={inv_stats['avg_pf']}")

    print("-----------------------------Battery Results---------------------------")
    print(f"Avg SOC [%] {batt_stats['avg_soc']} Low SOC [%]= {batt_stats['min_soc']} Eff [%]= {batt_stats['efficiency']}")

def print_anomalies(warnings: list[str], site_name: str) -> None:
    """Print anomaly warnings"""
    if not warnings:
        print("-----------------------------Anomaly Check-----------------------------")
        print("✅ No anomalies detected.")
        return
    print("-----------------------------WARNINGS---------------------------------")
    for w in warnings:
        print(f"  [!] {w}")

# ─── MAIN MULTI-SITE LOOP ────────────────────────────────────────────────────
def main() -> None:
    """Main function - loops through ALL sites"""
    parser = argparse.ArgumentParser(description="Multi-Site Victron VRM Monitoring")
    parser.add_argument("--start", default="2026-04-20, 00:00", help="Start date")
    parser.add_argument("--end", default="2026-05-07, 00:00", help="End date")
    parser.add_argument("--timezone", "-tz", type=int, default=3, help="UTC offset")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("."), help="Output directory")
    parser.add_argument("--cache-ttl", type=float, default=1.0, help="Cache TTL in hours")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    token = os.environ.get("VRM_API_TOKEN")
    if not token:
        logger.error("VRM_API_TOKEN not found")
        sys.exit(1)

    session = create_session(token)
    timezone = datetime.timedelta(hours=args.timezone)
    start_unix = to_unix(args.start)
    end_unix = to_unix(args.end)
    start_date = datetime.datetime.strptime(args.start, DATE_INPUT_FMT).date()
    end_date = datetime.datetime.strptime(args.end, DATE_INPUT_FMT).date()
    date_range = f"{start_date}to{end_date}"

    print(f"\n{'='*80}")
    print(f"MULTI-SITE MONITORING AUTOMATION")
    print(f"Processing {len(DEFAULT_SITES)} sites | Period: {args.start} to {args.end}")
    print(f"{'='*80}\n")

    # ─── LOOP THROUGH ALL SITES ───────────────────────────────────────────────
    for site_name, config in DEFAULT_SITES.items():
        print(f"\n📍 Processing: {site_name}...")

        site_id = str(config["id"])
        output_dir = args.output_dir / site_name
        output_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = output_dir / ".cache" if args.cache_ttl > 0 else None

        try:
            # Fetch all data for this site
            results = fetch_all(session, site_id, start_unix, end_unix, cache_dir, args.cache_ttl)
            if not results:
                logger.warning(f"Skipping {site_name} — no data fetched")
                continue

            # Process MPPT, inverter, battery
            df_mppt, mppt_stats = process_mppts([results["mppt"]], config["mppt_w"], timezone)
            df_inv, inv_stats = process_inverter(results["inverter"], config["inv_kva"], timezone)
            df_batt, batt_stats = process_battery(results["battery"], config["batt_kwh"], timezone)

            if not all([df_mppt is not None, df_inv is not None, df_batt is not None]):
                logger.warning(f"Skipping {site_name} — processing failed")
                continue

            # Print report and anomalies
            print_report(mppt_stats, inv_stats, batt_stats, site_name, args.start, args.end)
            anomalies = check_anomalies(mppt_stats, inv_stats, batt_stats)
            print_anomalies(anomalies, site_name)

            # Save CSVs
            df_mppt.to_csv(output_dir / f"{site_name}MPPTS_{date_range}.csv")
            df_inv.to_csv(output_dir / f"{site_name}INVERTERS_{date_range}.csv")
            df_batt.to_csv(output_dir / f"{site_name}Battery_{date_range}.csv")

            # Generate charts
            if not args.no_charts:
                hourly = pd.Grouper(key="Date", freq="h", sort=True)
                df_chart = pd.DataFrame({
                    "Production [Wh]": df_mppt.groupby(hourly)["Total productionIn [Wh]"].sum(),
                    "Consumption cover by Victron [Wh]": df_inv.groupby(hourly)["Total energy com [Wh]"].sum(),
                    "Avg SOC [%]": df_batt.groupby(hourly)["SOC [%]"].mean(),
                    "Max SOC [%]": df_batt.groupby(hourly)["SOC [%]"].max(),
                    "Min SOC [%]": df_batt.groupby(hourly)["SOC [%]"].min(),
                })
                generate_charts(df_chart, site_name, date_range, output_dir)

            logger.info(f"✅ {site_name} completed — saved to {output_dir}")

        except Exception as e:
            logger.error(f"❌ {site_name} failed: {e}")
            continue

    print(f"\n{'='*80}")
    print(f"✅ MONITORING COMPLETE - All sites processed")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
