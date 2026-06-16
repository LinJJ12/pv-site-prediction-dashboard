from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from scipy.spatial import cKDTree

from api_server import classify_pvpi, get_nasa_solar_data, predict_simple_value

try:
    from flask_cors import CORS
except ImportError:
    def CORS(app):
        return app

try:
    import torch
    import torch.nn.functional as F
    from torch_geometric.data import Data
    from torch_geometric.nn import GATConv
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent

app = Flask(__name__)
CORS(app)

model_package = None
gat_model = None
use_full_model = False


if TORCH_AVAILABLE:
    class GATModel(torch.nn.Module):
        def __init__(self, in_channels, hidden_channels=64, heads=4, dropout=0.25, num_classes=3):
            super().__init__()
            self.dropout = dropout
            self.conv1 = GATConv(in_channels, hidden_channels, heads=heads, dropout=dropout)
            self.conv2 = GATConv(hidden_channels * heads, hidden_channels, heads=1, concat=False, dropout=dropout)
            self.norm = torch.nn.LayerNorm(hidden_channels)
            self.reg_head = torch.nn.Sequential(
                torch.nn.Linear(hidden_channels, hidden_channels // 2),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout),
                torch.nn.Linear(hidden_channels // 2, 1),
            )
            self.cls_head = torch.nn.Sequential(
                torch.nn.Linear(hidden_channels, hidden_channels // 2),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout),
                torch.nn.Linear(hidden_channels // 2, num_classes),
            )
            self.skip_reg = torch.nn.Linear(in_channels, 1)

        def forward(self, x, edge_index):
            h = F.elu(self.conv1(x, edge_index))
            h = F.dropout(h, p=self.dropout, training=self.training)
            h = F.elu(self.conv2(h, edge_index))
            h = self.norm(h)
            reg = self.reg_head(h).squeeze(-1) + 0.15 * self.skip_reg(x).squeeze(-1)
            logits = self.cls_head(h)
            return reg, logits


K_NEIGHBORS = 10
MODEL_LEVEL_LABELS = {
    "low": "约束区",
    "medium": "备选区",
    "high": "适宜区",
}
MODEL_LEVEL_COLORS = {
    "约束区": "#ff6b6b",
    "备选区": "#f3df54",
    "适宜区": "#27e7f3",
    "优选区": "#00ff88",
}
MODEL_LEVEL_SUITABILITY = {
    "约束区": "低",
    "备选区": "中等",
    "适宜区": "高",
    "优选区": "极高",
}


def load_full_model():
    global model_package, gat_model, use_full_model
    model_path = PROJECT_ROOT / "models" / "models" / "model_gat_gbdt_pvssi.pkl"
    if not model_path.exists():
        return False

    try:
        with open(model_path, "rb") as f:
            model_package = pickle.load(f)

        if TORCH_AVAILABLE and "gat_state_dict" in model_package:
            params = model_package["gat_params"]
            gat_model = GATModel(
                in_channels=params["in_channels"],
                hidden_channels=params["hidden_channels"],
                heads=params["heads"],
                dropout=params["dropout"],
                num_classes=params["num_classes"],
            )
            gat_model.load_state_dict(model_package["gat_state_dict"], strict=True)
            gat_model.eval()
            use_full_model = True
        elif "gbdt_models" in model_package:
            use_full_model = True
        return use_full_model
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        model_package = None
        gat_model = None
        use_full_model = False
        return False


load_full_model()


def _iter_gbdt_models(gbdt_models):
    if isinstance(gbdt_models, dict):
        gbdt_models = list(gbdt_models.values())
    for item in gbdt_models:
        if isinstance(item, tuple) and len(item) >= 2:
            yield item[1]
        else:
            yield item


def transform_with_fitted_gbdt(X, scaler, gbdt_models):
    X_sc = scaler.transform(X)
    preds = [model.predict(X_sc).reshape(-1, 1) for model in _iter_gbdt_models(gbdt_models)]
    return np.column_stack([X_sc] + preds).astype(np.float32)


def build_knn_edge_index(xy, k=K_NEIGHBORS):
    tree = cKDTree(xy)
    k_eff = min(k + 1, len(xy))
    _, indices = tree.query(xy, k=k_eff)
    src, dst = [], []
    for i in range(len(xy)):
        for j in np.atleast_1d(indices[i])[1:]:
            src.extend([i, int(j)])
            dst.extend([int(j), i])
    return torch.tensor([src, dst], dtype=torch.long)


def _build_spatial_features(lat, lon, solar_data, model_package):
    ghi_mean = float(solar_data["ghi_annual_mean"])
    ghi_std = float(solar_data["ghi_annual_std"])
    temp_mean = float(solar_data["temp_annual_mean"])
    temp_std = float(solar_data["temp_annual_std"])
    precip_annual = float(solar_data["precip_annual_mean"])

    x_m = (lon - 105) * 111000 * np.cos(np.radians(lat))
    y_m = (lat - 35) * 111000

    train_xy = model_package["train_xy"]
    tree = cKDTree(train_xy)
    agglomeration = len(tree.query_ball_point([x_m, y_m], r=50000))
    dist_m, _ = tree.query([x_m, y_m], k=1)
    nearest_station_km = float(dist_m) / 1000.0

    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    pos_x = float(np.cos(lat_rad) * np.cos(lon_rad))
    pos_y = float(np.cos(lat_rad) * np.sin(lon_rad))
    pos_z = float(np.sin(lat_rad))
    log_area = float(np.log1p(model_package["train_df_minimal"]["area_km2"].median()))

    feature_values = [
        lon,
        lat,
        pos_x,
        pos_y,
        pos_z,
        log_area,
        ghi_mean,
        ghi_std,
        temp_mean,
        temp_std,
        max(0, precip_annual),
        float(agglomeration),
        nearest_station_km,
    ]
    return {
        "feature_values": feature_values,
        "x_m": x_m,
        "y_m": y_m,
        "agglomeration": agglomeration,
        "ghi_mean": ghi_mean,
        "ghi_std": ghi_std,
        "temp_mean": temp_mean,
        "temp_std": temp_std,
        "precip_annual": precip_annual,
    }


INFERENCE_VERSION = "v3-nasa-gat-reg"


def _pvssi_to_pvpi(pvssi_value):
    pvssi_clipped = float(np.clip(pvssi_value, 0.0, 100.0))
    return max(0.1, min(0.99, pvssi_clipped / 100.0))


def _gbdt_pvpi(gbdt_pred_mean, model_package):
    y_min = float(model_package["train_df_minimal"]["PVSSI_rule"].min())
    y_max = float(model_package["train_df_minimal"]["PVSSI_rule"].max())
    if y_max <= y_min:
        return 0.5
    return max(0.1, min(0.99, (gbdt_pred_mean - y_min) / (y_max - y_min)))


def _resolve_level(level_key, pvpi):
    level = MODEL_LEVEL_LABELS.get(level_key)
    if level is None:
        level, _, _ = classify_pvpi(pvpi)
    elif pvpi >= 0.8 and level_key == "high":
        level = "优选区"
    return level


def predict_simple(lat, lon):
    solar_data = get_nasa_solar_data(lat, lon)
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


def _full_prediction(lat, lon):
    if model_package is None:
        raise RuntimeError("完整模型未加载")

    solar_data = get_nasa_solar_data(lat, lon)
    spatial = _build_spatial_features(lat, lon, solar_data, model_package)
    feature_values = spatial["feature_values"]
    X_cand = np.array([feature_values], dtype=np.float32)

    gbdt_models = model_package["gbdt_models"]
    x_scaler = model_package["x_scaler"]
    y_scaler = model_package["y_scaler"]

    gbdt_scaled_preds = [float(m.predict(x_scaler.transform(X_cand))[0]) for m in _iter_gbdt_models(gbdt_models)]
    gbdt_pred_mean = float(np.mean(gbdt_scaled_preds))

    pvssi_model = gbdt_pred_mean
    pvpi_source = "gbdt"
    gat_probs = None

    if TORCH_AVAILABLE and gat_model is not None and "train_aug_features" in model_package:
        X_train = model_package["train_features"].astype(np.float32)
        X_combined = np.vstack([X_train, X_cand])
        X_aug_combined = transform_with_fitted_gbdt(X_combined, x_scaler, gbdt_models)

        xy_combined = np.vstack([
            model_package["train_xy"],
            np.array([[spatial["x_m"], spatial["y_m"]]], dtype=float),
        ])
        edge_index = build_knn_edge_index(xy_combined, k=K_NEIGHBORS)
        new_idx = len(X_train)

        data = Data(
            x=torch.tensor(X_aug_combined, dtype=torch.float32),
            edge_index=edge_index,
        )
        with torch.no_grad():
            reg_out, cls_out = gat_model(data.x, data.edge_index)
            reg_value = reg_out[new_idx]
            if hasattr(reg_value, "dim") and reg_value.dim() > 0:
                reg_value = reg_value.squeeze()
            pvssi_model = float(
                y_scaler.inverse_transform(reg_value.detach().cpu().numpy().reshape(-1, 1))[0, 0]
            )
            pvpi_source = "gat_reg"
            gat_probs = F.softmax(cls_out[new_idx], dim=0).cpu().numpy()

    pvpi = _pvssi_to_pvpi(pvssi_model)
    level, level_color, suitability = classify_pvpi(pvpi)

    result = {
        "lat": lat,
        "lon": lon,
        "pvpi": round(pvpi, 4),
        "pvssi": round(pvpi, 4),
        "pvssi_model": round(float(np.clip(pvssi_model, 0.0, 100.0)), 4),
        "level": level,
        "level_color": level_color,
        "suitability": suitability,
        "model_type": "GAT+GBDT集成模型",
        "inference_version": INFERENCE_VERSION,
        "pvpi_source": pvpi_source,
        "gbdt_pred": round(gbdt_pred_mean, 4),
        "agglomeration": spatial["agglomeration"],
        "solar_data": {
            "ghi_annual_mean": round(spatial["ghi_mean"], 2),
            "ghi_annual_std": round(spatial["ghi_std"], 2),
            "temp_annual_mean": round(spatial["temp_mean"], 2),
            "temp_annual_std": round(spatial["temp_std"], 2),
            "precip_annual_mean": round(max(0, spatial["precip_annual"]), 2),
            "source": solar_data.get("source", "unknown"),
        },
    }
    if gat_probs is not None:
        result["gat_probs"] = [round(float(p), 4) for p in gat_probs]
    return result


def predict_full(lat, lon):
    return _full_prediction(lat, lon)


@app.route("/api/predict", methods=["GET"])
def predict():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        mode = request.args.get("mode", "simple")
        result = predict_full(lat, lon) if mode == "full" else predict_simple(lat, lon)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    y_min = float(model_package["train_df_minimal"]["PVSSI_rule"].min()) if model_package else None
    y_max = float(model_package["train_df_minimal"]["PVSSI_rule"].max()) if model_package else None
    return jsonify({
        "model_loaded": model_package is not None,
        "model_type": "GAT+GBDT集成模型" if use_full_model else "简化公式",
        "inference_version": INFERENCE_VERSION,
        "feature_cols": model_package["feature_cols"] if model_package else None,
        "levels": model_package["id_to_level"] if model_package else None,
        "y_min": y_min,
        "y_max": y_max,
        "gbdt_models_type": type(model_package["gbdt_models"]).__name__ if model_package else None
    })


@app.route("/api/debug_model", methods=["GET"])
def debug_model():
    try:
        lat = float(request.args.get("lat", 31.23))
        lon = float(request.args.get("lon", 121.47))
        result = _full_prediction(lat, lon)
        return jsonify({
            "input_lat": lat,
            "input_lon": lon,
            "feature_cols": model_package["feature_cols"],
            "pvpi": result["pvpi"],
            "pvssi_model": result.get("pvssi_model"),
            "gbdt_pred": result.get("gbdt_pred"),
            "level": result.get("level"),
            "gat_probs": result.get("gat_probs"),
            "solar_data": result.get("solar_data"),
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/toggle_mode", methods=["POST"])
def toggle_mode():
    global use_full_model
    mode = (request.get_json() or {}).get("mode", "simple")
    if mode == "full":
        use_full_model = model_package is not None or load_full_model()
    else:
        use_full_model = False
    return jsonify({
        "success": True,
        "mode": "full" if use_full_model else "simple",
        "message": f'已切换到 {("完整模型" if use_full_model else "简化公式")}',
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
