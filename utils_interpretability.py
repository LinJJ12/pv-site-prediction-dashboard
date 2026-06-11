"""Model interpretability helpers for real trained models."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

warnings.filterwarnings("ignore")
plt.rcParams["font.family"] = "DejaVu Sans"


class ModelInterpreter:
    """SHAP-based interpreter for fitted tree models."""

    def __init__(self, model, X_train, X_test, feature_names):
        self.model = model
        self.X_train = X_train
        self.X_test = X_test
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None

    def compute_shap_values(self, sample_size=100):
        """Compute SHAP values for the provided test set."""
        self.explainer = shap.TreeExplainer(self.model)
        self.shap_values = self.explainer.shap_values(self.X_test)
        return self.shap_values

    def _class_shap_values(self):
        if self.shap_values is None:
            raise RuntimeError("Call compute_shap_values() before plotting.")
        if isinstance(self.shap_values, list):
            return self.shap_values[1]
        return self.shap_values

    def plot_summary(self, max_display=20, output_path="shap_summary.png"):
        """Save a SHAP summary plot."""
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            self._class_shap_values(),
            self.X_test,
            feature_names=self.feature_names,
            max_display=max_display,
            show=False,
        )
        plt.title("SHAP Feature Importance Summary", fontsize=14, fontweight="bold", pad=20)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return output_path

    def plot_waterfall(self, sample_idx=0, output_path=None):
        """Save a SHAP waterfall plot for one sample."""
        if self.explainer is None:
            raise RuntimeError("Call compute_shap_values() before plotting.")
        output_path = output_path or f"shap_waterfall_sample_{sample_idx}.png"
        shap_values = self._class_shap_values()
        base_value = self.explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[1]
        explanation = shap.Explanation(
            values=shap_values[sample_idx],
            base_values=base_value,
            data=self.X_test[sample_idx],
            feature_names=self.feature_names,
        )
        plt.figure(figsize=(10, 6))
        shap.waterfall_plot(explanation, show=False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return output_path

    def plot_force(self, sample_idx=0, output_path=None):
        """Save a force-style plot for one sample."""
        if self.explainer is None:
            raise RuntimeError("Call compute_shap_values() before plotting.")
        output_path = output_path or f"shap_force_sample_{sample_idx}.png"
        shap_values = self._class_shap_values()
        base_value = self.explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[1]
        shap.force_plot(
            base_value,
            shap_values[sample_idx],
            self.X_test[sample_idx],
            feature_names=self.feature_names,
            matplotlib=True,
            show=False,
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return output_path

    def plot_dependence(self, feature_idx=0, output_path=None):
        """Save a SHAP dependence plot."""
        output_path = output_path or f"shap_dependence_feature_{feature_idx}.png"
        shap.dependence_plot(
            feature_idx,
            self._class_shap_values(),
            self.X_test,
            feature_names=self.feature_names,
            show=False,
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()
        return output_path

    def get_feature_importance(self):
        """Return mean absolute SHAP importance by feature."""
        importance = np.abs(self._class_shap_values()).mean(axis=0)
        return (
            pd.DataFrame({"feature": self.feature_names, "importance": importance})
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )


if __name__ == "__main__":
    raise SystemExit("Import ModelInterpreter and pass real train/test data before use.")
