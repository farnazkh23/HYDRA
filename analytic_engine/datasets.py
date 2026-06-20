# analytic_engine/datasets.py
import torch
import numpy as np
from typing import Dict


class ComplianceMultiModalDataset:
    def __init__(self):
        """
        Automated data imputation & PyTorch tensor processing module.
        Normalizes multi-layered behavioral profiles into structural risk arrays.
        """
        # Baseline statistical priors used for imputation overrides
        self.fallback_imputations = {
            "severity_score": 0.0,
            "total_active_edges": 4.0,
            "mutation_ratio": 0.0
        }

    def impute_and_vectorize(self, time_series_metrics: Dict, graph_metrics: Dict) -> torch.Tensor:
        """
        Ingests unstructured state metrics, handles missing fields, and returns a continuous tensor.

        Packed Feature Dimension Layout:
        - X[0]: Volumetric Anomaly Indicator Flag (0.0 or 1.0)
        - X[1]: Structural Volumetric Severity Score (Imputed if missing)
        - X[2]: Active Graph Topological Edge Count (Imputed if missing)
        - X[3]: Core Relationship Mutation Ratio (Added / Total Mutations)
        """
        # 1. Process Layer 2 Statistical Signals
        anomaly_flag = 1.0 if time_series_metrics.get("anomaly_flag", False) else 0.0

        severity_score = time_series_metrics.get("severity_score")
        if severity_score is None or np.isnan(float(severity_score)):
            severity_score = self.fallback_imputations["severity_score"]
        else:
            severity_score = float(severity_score)

        # 2. Process Layer 1 Graph Topology Parameters
        total_edges = graph_metrics.get("total_active_edges")
        if total_edges is None or np.isnan(float(total_edges)):
            total_edges = self.fallback_imputations["total_active_edges"]
        else:
            total_edges = float(total_edges)

        added = float(graph_metrics.get("triples_added_count", 0.0))
        deleted = float(graph_metrics.get("triples_deleted_count", 0.0))

        # Safe mathematical ratio check protecting against division-by-zero crashes
        if (added + deleted) == 0.0:
            mutation_ratio = self.fallback_imputations["mutation_ratio"]
        else:
            mutation_ratio = added / (added + deleted)

        # 3. Assemble Concatenated Matrix Row (X)
        feature_array = np.array([
            anomaly_flag,
            severity_score,
            total_edges,
            mutation_ratio
        ], dtype=np.float32)

        # Convert straight to a PyTorch tensor with explicit 2D batch dimension shape [1, 4]
        return torch.tensor(feature_array, dtype=torch.float32).unsqueeze(0)


# --- VERIFICATION LOOP ---
if __name__ == "__main__":
    print("Testing Step 3: Imputation and PyTorch Tensor Processing Pipeline...")

    # Mirroring the active dictionaries from your specific live terminal logs
    mock_live_ts = {'forecasted_mean': 150.03392, 'anomaly_flag': True, 'severity_score': 16662.8986}
    mock_live_graph = {'total_active_edges': 8.0, 'triples_added_count': 1.0, 'triples_deleted_count': 1.0}

    # Mirroring a corrupted/incomplete ingestion signal to stress-test your imputation bounds
    corrupted_ts = {'forecasted_mean': None, 'anomaly_flag': False, 'severity_score': None}
    corrupted_graph = {'total_active_edges': float('nan'), 'triples_added_count': 0.0, 'triples_deleted_count': 0.0}

    processor = ComplianceMultiModalDataset()

    clean_X = processor.impute_and_vectorize(mock_live_ts, mock_live_graph)
    imputed_X = processor.impute_and_vectorize(corrupted_ts, corrupted_graph)

    print(f"\nProcessed Tensor Vector Shape: {clean_X.shape}")
    print(f"Clean Live Data Matrix Row (X): {clean_X}")
    print(f"Imputed Data Matrix Row (X):    {imputed_X}")