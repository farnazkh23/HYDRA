# main.py
import asyncio
import pandas as pd
from analytic_engine.time_series import InternalTelemetryEngine
from analytic_engine.graph_fusion import TemporalGraphFusionEngine, StructuralResolutionPayload, KnowledgeTriple
from analytic_engine.datasets import ComplianceMultiModalDataset
from analytic_engine.models import BaseSurvivalModel
from analytic_engine.router import CostAwareCascadingRouter


async def execute_hydra_pipeline(client_id: str, raw_public_signal: str, incoming_triples: list,
                                 transaction_history: pd.DataFrame):
    """
    Main Event-Driven Loop B Orchestrator.
    Triggers dynamically when Loop A fires a REGIME_SHIFT or DRIFT_ALERT.
    """
    print(f"\n⚡ [Hydra Core Action] Processing pipeline ingestion payload for customer: {client_id}")

    # 1. Run Live Layer 2 Internal Telemetry Checking
    ts_engine = InternalTelemetryEngine()
    _, ts_metrics = ts_engine.detect_volumetric_anomaly(transaction_history)

    # 2. Run Local Temporal Graph Fusion Update
    graph_engine = TemporalGraphFusionEngine()
    payload = StructuralResolutionPayload(
        chain_of_thought="Analyzing edge structural mutations from ingestion against baseline KYC topology.",
        detected_triples=incoming_triples
    )
    graph_metrics = graph_engine.execute_triple_resolution(payload, timestamp="2026-06-20T11:45:00Z")
    graph_engine.close()

    # 3. Vectorize Through Automated Imputation Layers
    data_assembler = ComplianceMultiModalDataset()
    matrix_X = data_assembler.impute_and_vectorize(ts_metrics, graph_metrics)

    # 4. Compute Continuous Deep Survival Horizon Timeline
    survival_model = BaseSurvivalModel()
    predicted_t, uncertainty = survival_model.calculate_time_to_decay(matrix_X)

    # 5. Route Through Budget-Aware Guardrailed Output Layer
    router = CostAwareCascadingRouter()
    final_audit_log = router.evaluate_routing_tier(client_id, predicted_t, raw_public_signal)

    print("\n================== DEFINITIVE AUDIT LOG OUTPUT ==================")
    print(f"Risk Rating Token : {final_audit_log.risk_token}")
    print(f"Compliance Audit  : {final_audit_log.chain_of_thought}")
    print(f"Source Citations  : {final_audit_log.audit_citations}")
    print(f"Pipeline Budget   : {router.token_ledger}")
    print("=================================================================\n")
    return final_audit_log


# --- RUN FULL LOOP B SIMULATION END-TO-END ---
if __name__ == "__main__":
    # Generate mock transaction data mirroring the exact dormancy break spike profile your engine caught
    dates = pd.date_range(start="2026-05-01", end="2026-06-18", freq="D")
    dormancy_break_volumes = [150 if i < (len(dates) - 1) else 2500000 for i in range(len(dates))]

    history_df = pd.DataFrame({
        "timestamp": dates,
        "value": dormancy_break_volumes
    })

    # Sample triple mutations generated from corporate registration documents
    mock_triples = [
        KnowledgeTriple(subject="AlphaTech GmbH", predicate="HAS_BUSINESS_MODEL", object="SaaS_Enterprise",
                        modification_type="DELETED"),
        KnowledgeTriple(subject="AlphaTech GmbH", predicate="HAS_BUSINESS_MODEL", object="Crypto_Trading",
                        modification_type="ADDED")
    ]

    # Execute the master async wrapper loop
    asyncio.run(execute_hydra_pipeline(
        client_id="CH-4491",
        raw_public_signal="ZEFIX platform updates confirm business purpose change to active digital currency broker.",
        incoming_triples=mock_triples,
        transaction_history=history_df
    ))