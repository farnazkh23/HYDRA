# analytic_engine/datasets.py
import torch
import numpy as np
from typing import Dict


class ComplianceMultiModalDataset:
    def __init__(self):
        """
        Converts graph structural mutations and statistical time-series anomalies
        into a unified, multi-modal feature matrix (X) for deep survival models.
        """
        pass

    def extract_feature_vector(self, time_series_metrics: Dict, graph_payload: Dict) -> torch.Tensor:
        """
        Maps Topology + Timeline Metrics to a continuous space.

        Vector Mapping Structure:
        - X[0]: Volumetric Anomaly Flag (0 or 1)
        - X[1]: Structural Volumetric Severity Score
        - X[2]: Total Active Graph Relationships Count
        - X[3]: Core Risk Mutation Ratio (Added / Total)
        """
        # 1. Process Layer 2 Statistical Metrics from time_series.py
        anomaly_flag = 1.0 if time_series_metrics.get("anomaly_flag", False) else 0.0
        severity_score = float(time_series_metrics.get("severity_score", 0.0))

        # 2. Process Layer 1 Graph Topology Parameters from graph_fusion.py
        total_edges = float(graph_payload.get("total_active_edges", 0.0))
        added_triples = float(graph_payload.get("triples_added_count", 0.0))
        deleted_triples = float(graph_payload.get("triples_deleted_count", 0.0))

        # Avoid division by zero when calculating risk ratio
        denominator = (added_triples + deleted_triples + 1e-6)
        mutation_ratio = added_triples / denominator

        # 3. Assemble Concatenated Matrix Row (X)
        feature_array = np.array([
            anomaly_flag,
            severity_score,
            total_edges,
            mutation_ratio
        ], dtype=np.float32)

        # Convert straight to a PyTorch tensor for the neural network backend [Batch Size, Feature Dimension]
        return torch.tensor(feature_array).unsqueeze(0)


# --- VERIFICATION BLOCK ---
if __name__ == "__main__":
    print("Testing Step 3: Generating Multi-Modal Input Vector Matrix (X)...")

    # Simulating outputs directly from your verified time_series.py and graph_fusion.py metrics
    mock_ts_metrics = {'forecasted_mean': 2500000, 'anomaly_flag': False, 'severity_score': 0.0}
    mock_graph_metrics = {'total_active_edges': 8.0, 'triples_added_count': 1.0, 'triples_deleted_count': 1.0}

    assembler = ComplianceMultiModalDataset()
    matrix_X = assembler.extract_feature_vector(mock_ts_metrics, mock_graph_metrics)

    print(f"Generated Tensor Shape: {matrix_X.shape}")
    print(f"Matrix X Values: {matrix_X}")