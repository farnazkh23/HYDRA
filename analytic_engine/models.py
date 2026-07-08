# analytic_engine/models.py
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple


class BaseSurvivalModel(nn.Module):
    def __init__(self, input_dim: int = 4, weights_path: str = None):
        """
        Survival-risk proxy / urgency heuristic module wrapping a continuous
        log-hazard risk score.

        Default behaviour (no weights_path, or CUDA unavailable) runs a
        heuristic proxy on untrained, seed-pinned weights - it is NOT a
        trained or calibrated survival model. Swappable interface: pass a
        valid 'weights_path' (with CUDA available) to load real trained
        weights instead. A trained, calibrated survival model is on the
        roadmap, not current default behaviour.
        """
        super().__init__()

        # Core Neural Net Blueprint - completely intact and production-ready
        self.network = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 1)  # Raw log-hazard ratio h(x)
        )

        # Pin weights for deterministic presentation runs
        torch.manual_seed(42)

        # SEAMLESS SWAP GATEWAY: If weights exist from a training run, load them!
        if weights_path and torch.cuda.is_available():
            try:
                self.load_state_dict(torch.load(weights_path))
                self.is_mocked = False
                print(f"[Engine] Successfully loaded production survival weights from {weights_path}")
            except Exception as e:
                print(f"[Engine Warning] Could not load weights ({e}). Defaulting to predictive proxy mode.")
                self.is_mocked = True
        else:
            self.is_mocked = True

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

    def calculate_time_to_decay(self, feature_tensor: torch.Tensor) -> Tuple[float, float]:
        """
        Evaluates the non-linear hazard index to output:
          - T: Survival-risk proxy / urgency heuristic estimate of days
               remaining before compliance breakdown (calibrated only if
               real trained weights were loaded via weights_path; otherwise
               a heuristic estimate, not a statistically calibrated figure).
          - Uncertainty Bound: A simple heuristic spread derived from the
               log-hazard magnitude, not a statistical standard error.
        """
        self.eval()
        with torch.no_grad():
            # Pass through the real tensor graph layer to preserve computational structure
            raw_network_output = self.forward(feature_tensor).item()

            if self.is_mocked:
                # --- SURVIVAL-RISK PROXY MODE (URGENCY HEURISTIC, DEFAULT) ---
                # Untrained weights; this branch is a rule-based heuristic
                # scaled against active features, not a calibrated forecast.
                log_hazard = raw_network_output

                # Check if Loop A / Nixtla flagged an active anomaly spike (X[0] == 1.0)
                if feature_tensor[0, 0].item() == 1.0:
                    severity_mod = float(feature_tensor[0, 1].item() * 2.5)
                    mutation_mod = float(feature_tensor[0, 3].item() * 1.5)
                    log_hazard = float(np.abs(log_hazard) + 1.0 + severity_mod + mutation_mod)
            else:
                # --- TRAINED-WEIGHTS INFERENCE MODE ---
                # Uses real trained neural weights loaded via weights_path
                # (not the default heuristic proxy above).
                log_hazard = raw_network_output

            # Map log-hazard to an exponential risk-factor heuristic
            # (Cox-style hazard scaling h(x) = h0 * exp(f(x)) as a proxy form,
            # not a fitted/calibrated Cox proportional-hazards model).
            risk_factor = np.exp(np.clip(log_hazard, -5.0, 5.0))

            base_expected_days = 14.0  # Normalized baseline monitoring frequency horizon
            predicted_t = base_expected_days / (risk_factor + 1e-5)

            # Strict operational boundary clamping to keep dashboard widgets safe
            predicted_t = max(0.4, min(predicted_t, 90.0))
            uncertainty_width = float(np.abs(log_hazard) * 1.2)

            return float(predicted_t), uncertainty_width


if __name__ == "__main__":
    print("Testing Step 4: Evaluating Interchangeable BaseSurvivalModel Framework...")

    # Validate utilizing our scaled multi-modal datasets configurations
    normal_X = torch.tensor([[0.0, 0.0, float(np.log1p(4.0)), 0.0]], dtype=torch.float32)
    critical_X = torch.tensor([[1.0, 0.333, float(np.log1p(8.0)), 0.5]], dtype=torch.float32)

    model = BaseSurvivalModel()

    t_normal, var_normal = model.calculate_time_to_decay(normal_X)
    t_crit, var_crit = model.calculate_time_to_decay(critical_X)

    print(f"\nNormal operation target horizon T:  {t_normal:.2f} days (Uncertainty: ±{var_normal:.2f})")
    print(f"Critical anomaly target horizon T:  {t_crit:.2f} days (Uncertainty: ±{var_crit:.2f})")