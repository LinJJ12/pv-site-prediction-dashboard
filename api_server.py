from pathlib import Path
import time

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from scipy.spatial import cKDTree

from utils_solar_data import SolarRadiationAPI

try:
    from flask_cors import CORS
except ImportError:
    def CORS(app):
        return app

PROJECT_ROOT = Path(__file__).resolve().parent

app = Flask(__name__)
CORS(app)
nasa_api = SolarRadiationAPI()
station_data = None
station_tree = None


def load_station_data():
    global station_data, station_tree
    if station_data is not None:
        return station_data, station_tree

    # 尝试多个可能的数据文件路径
    possible_paths = [
        PROJECT_ROOT / "solar_data_output" / "pv_stations_mcdm_scored.csv",
        PROJECT_ROOT / "dashboard" / "public" / "data" / "pv_stations_mcdm_scored.csv",
        PROJECT_ROOT / "dashboard" / "dist" / "data" / "pv_stations_mcdm_scored.csv",
    ]
    
    data_path = None
    for path in possible_paths:
        if path.exists():
            data_path = path
            break
    
    if data_path is None:
        raise FileNotFoundError(f"无法找到光伏电站数据文件。已搜索路径: {possible_paths}")
    
    station_data = pd.read_csv(data_path)
    station_tree = cKDTree(station_data[["lon", "lat"]].to_numpy())
    return station_data, station_tree


def get_nasa_solar_data(lat, lon, retries=3):
    last_error = None
    for attempt in range(retries):
        solar_data = nasa_api.get_solar_data(lat, lon, start_year=2020, end_year=2023)
        if solar_data is not None:
            solar_data["source"] = "NASA POWER 2020-2023"
            return solar_data
        last_error = f"NASA POWER 第 {attempt + 1} 次请求无数据"
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(
        f"无法从 NASA POWER 获取 ({lat}, {lon}) 的气候数据，请检查网络后重试。{last_error or ''}"
    )


def get_real_solar_data(lat, lon):
    solar_data = nasa_api.get_solar_data(lat, lon, start_year=2020, end_year=2023)
    if solar_data is not None:
        solar_data["source"] = "NASA POWER 2020-2023"
        return solar_data

    stations, tree = load_station_data()
    distance, index = tree.query([lon, lat], k=1)
    row = stations.iloc[int(index)]
    return {
        "ghi_annual_mean": row["ghi_mean"],
        "ghi_annual_std": row["ghi_std"],
        "temp_annual_mean": row["temp_mean"],
        "temp_annual_std": row["temp_std"],
        "precip_annual_mean": row["precip_annual"],
        "source": f'nearest real station: {row["province"]} #{int(row["index"])}',
        "nearest_station_distance_deg": float(distance),
    }


def classify_pvpi(pvpi):
    if pvpi >= 0.8:
        return "优选区", "#00ff88", "极高"
    if pvpi >= 0.6:
        return "适宜区", "#27e7f3", "高"
    if pvpi >= 0.4:
        return "备选区", "#f3df54", "中等"
    return "约束区", "#ff6b6b", "低"


def predict_simple_value(solar_data):
    ghi = round(float(solar_data["ghi_annual_mean"]), 2)
    temp = round(float(solar_data["temp_annual_mean"]), 2)
    temp_std = round(float(solar_data["temp_annual_std"]), 2)
    precip = round(float(solar_data["precip_annual_mean"]), 2)

    ghi_score = min(ghi / 6, 1)
    temp_score = min(max((25 - abs(temp - 15)) / 25, 0), 1)
    precip_score = min(max((1000 - precip) / 1000, 0), 1)
    stability_score = min(max((10 - temp_std) / 10, 0), 1)
    return max(0.1, min(0.95, round(0.3 * ghi_score + 0.2 * temp_score + 0.25 * precip_score + 0.25 * stability_score, 4)))


def predict_simple(lat, lon):
    solar_data = get_real_solar_data(lat, lon)
    pvpi = predict_simple_value(solar_data)
    level, level_color, suitability = classify_pvpi(pvpi)
    return {
        "lat": lat,
        "lon": lon,
        "pvpi": pvpi,
        "pvssi": pvpi,
        "level": level,
        "level_color": level_color,
        "suitability": suitability,
        "model_type": "简化公式",
        "solar_data": {
            "ghi_annual_mean": round(float(solar_data["ghi_annual_mean"]), 2),
            "ghi_annual_std": round(float(solar_data["ghi_annual_std"]), 2),
            "temp_annual_mean": round(float(solar_data["temp_annual_mean"]), 2),
            "temp_annual_std": round(float(solar_data["temp_annual_std"]), 2),
            "precip_annual_mean": round(max(0, float(solar_data["precip_annual_mean"])), 2),
            "source": solar_data.get("source", "unknown"),
        },
    }


@app.route("/api/predict", methods=["GET"])
def predict():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        solar_data = get_real_solar_data(lat, lon)
        pvpi = predict_simple_value(solar_data)
        level, level_color, suitability = classify_pvpi(pvpi)

        return jsonify({
            "lat": lat,
            "lon": lon,
            "pvpi": pvpi,
            "pvssi": pvpi,
            "level": level,
            "level_color": level_color,
            "suitability": suitability,
            "model_type": "简化公式",
            "solar_data": {
                "ghi_annual_mean": round(float(solar_data["ghi_annual_mean"]), 2),
                "ghi_annual_std": round(float(solar_data["ghi_annual_std"]), 2),
                "temp_annual_mean": round(float(solar_data["temp_annual_mean"]), 2),
                "temp_annual_std": round(float(solar_data["temp_annual_std"]), 2),
                "precip_annual_mean": round(max(0, float(solar_data["precip_annual_mean"])), 2),
                "source": solar_data.get("source", "unknown"),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"model_loaded": False, "model_type": "简化公式"})


@app.route("/api/toggle_mode", methods=["POST"])
def toggle_mode():
    return jsonify({"success": True, "mode": "simple", "message": "已切换到 简化公式"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
