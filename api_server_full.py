from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from scipy.spatial import cKDTree

from api_server import classify_pvpi, get_real_solar_data, predict_simple_value

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
            self.norm = torch.nn.BatchNorm1d(hidden_channels)
            self.reg_head = torch.nn.Sequential(
                torch.nn.Linear(hidden_channels, 32),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout),
                torch.nn.Linear(32, 1),
            )
            self.cls_head = torch.nn.Sequential(
                torch.nn.Linear(hidden_channels, 32),
                torch.nn.ReLU(),
                torch.nn.Dropout(dropout),
                torch.nn.Linear(32, num_classes),
            )
            self.skip_reg = torch.nn.Linear(in_channels, 1)

        def forward(self, x, edge_index):
            x_skip = x
            x = F.dropout(x, p=self.dropout, training=self.training)
            x = F.elu(self.conv1(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
            x = self.conv2(x, edge_index)
            x = self.norm(x)
            return self.reg_head(x) + self.skip_reg(x_skip), self.cls_head(x)


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
            gat_model.load_state_dict(model_package["gat_state_dict"], strict=False)
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


def _full_prediction(lat, lon):
    if model_package is None:
        raise RuntimeError("完整模型未加载")

    solar_data = get_real_solar_data(lat, lon)
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
    temp_penalty = 1 - 0.004 * abs(temp_mean - 25)
    climate_interact = temp_penalty * (ghi_mean / 5.0) * (1 - precip_annual / 2000)

    features = {
        "ghi_mean": ghi_mean,
        "ghi_std": ghi_std,
        "temp_mean": temp_mean,
        "temp_std": temp_std,
        "precip_annual": max(0, precip_annual),
        "agglomeration": agglomeration,
        "climate_interact": climate_interact,
        "area_km2": model_package["train_df_minimal"]["area_km2"].median(),
        "lon": lon,
        "lat": lat,
        "x_m": x_m,
        "y_m": y_m,
    }
    X = np.array([[features.get(col, 0) for col in model_package["feature_cols"]]])
    X_scaled = model_package["x_scaler"].transform(X)

    gbdt_preds = [model.predict(X_scaled) for model in model_package["gbdt_models"].values()]
    gbdt_pred_mean = float(np.mean(gbdt_preds))
    pvssi = float(model_package["y_scaler"].inverse_transform([[gbdt_pred_mean]])[0, 0])
    pvssi = max(0.1, min(1.0, pvssi))

    level = "备选区"
    gat_probs = None
    if TORCH_AVAILABLE and gat_model is not None and "train_aug_features" in model_package:
        _, indices = tree.query([x_m, y_m], k=5)
        X_aug = np.vstack([model_package["train_aug_features"], X_scaled])
        new_idx = len(model_package["train_aug_features"])
        edges = []
        for idx in np.atleast_1d(indices):
            edges.append([new_idx, int(idx)])
            edges.append([int(idx), new_idx])
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        data = Data(x=torch.tensor(X_aug, dtype=torch.float32), edge_index=edge_index)
        with torch.no_grad():
            _, cls_out = gat_model(data.x, data.edge_index)
            gat_probs = F.softmax(cls_out[new_idx], dim=0).cpu().numpy()
        level_id = int(np.argmax(gat_probs))
        level = model_package.get("id_to_level", {}).get(level_id, level)

    if level not in {"优选区", "适宜区", "备选区", "约束区"}:
        level, _, _ = classify_pvpi(pvssi)
    level_color = {"优选区": "#00ff88", "适宜区": "#27e7f3", "备选区": "#f3df54", "约束区": "#ff6b6b"}.get(level, "#27e7f3")
    suitability = {"优选区": "极高", "适宜区": "高", "备选区": "中等", "约束区": "低"}.get(level, "中等")

    result = {
        "lat": lat,
        "lon": lon,
        "pvpi": round(pvssi, 4),
        "pvssi": round(pvssi, 4),
        "level": level,
        "level_color": level_color,
        "suitability": suitability,
        "model_type": "GAT+GBDT集成模型",
        "gbdt_pred": round(gbdt_pred_mean, 4),
        "agglomeration": agglomeration,
        "solar_data": {
            "ghi_annual_mean": round(ghi_mean, 2),
            "ghi_annual_std": round(ghi_std, 2),
            "temp_annual_mean": round(temp_mean, 2),
            "temp_annual_std": round(temp_std, 2),
            "precip_annual_mean": round(max(0, precip_annual), 2),
            "source": solar_data.get("source", "unknown"),
        },
    }
    if gat_probs is not None:
        result["gat_probs"] = [round(float(p), 4) for p in gat_probs]
    return result


def predict_full(lat, lon):
    try:
        return _full_prediction(lat, lon)
    except Exception as e:
        fallback = predict_simple(lat, lon)
        fallback["model_type"] = "简化公式（完整模型失败后回退）"
        fallback["fallback_reason"] = str(e)
        return fallback


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
    return jsonify({
        "model_loaded": model_package is not None,
        "model_type": "GAT+GBDT集成模型" if use_full_model else "简化公式",
        "feature_cols": model_package["feature_cols"] if model_package else None,
        "levels": model_package["id_to_level"] if model_package else None,
    })


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
    app.run(host="0.0.0.0", port=5000, debug=True)
