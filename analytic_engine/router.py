# analytic_engine/router.py
from pydantic import BaseModel, Field
from typing import List, Literal
import instructor
from openai import OpenAI
import os


# --- COMPLIANCE MANDATED AUDIT SCHEMAS ---
class ComplianceAuditLog(BaseModel):
    risk_token: Literal["LOW_RISK", "ELEVATED_DRIFT", "CRITICAL_BREACH"] = Field(
        ..., description="Final risk classification layer based on combined multi-modal indicators."
    )
    chain_of_thought: str = Field(
        ..., description="Step-by-step audit rationale contrasting public indicators with internal KYC baselines."
    )
    audit_citations: List[str] = Field(
        ..., description="Verifiable string metrics matching from corporate registries or media strings."
    )


# --- COST-AWARE CASCADING ROUTER ENGINE ---
class CostAwareCascadingRouter:
    def __init__(self):
        """
        Implements AMINA's explicit token-tracking optimization architecture.
        """
        base_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock_key_for_dev"))
        self.instructor_client = instructor.from_openai(base_client)
        self.is_mock = os.getenv("OPENAI_API_KEY") is None

        # Operational budget tracking metrics
        self.token_ledger = {"cheap_tier_calls": 0, "heavy_tier_calls": 0, "total_cost_usd": 0.0}

    def evaluate_routing_tier(self, client_id: str, predicted_t: float, raw_payload: str) -> ComplianceAuditLog:
        """
        Evaluates remaining survival buffer (T) to determine the compute budget allocation.
        """
        # Tier 1: Safe Operational Path (T >= 7.0 days)
        if predicted_t >= 7.0:
            self.token_ledger["cheap_tier_calls"] += 1
            self.token_ledger["total_cost_usd"] += 0.0002

            return ComplianceAuditLog(
                risk_token="LOW_RISK",
                chain_of_thought=f"Automatic pass heuristic: Client stability timeline is secure at {predicted_t:.2f} days.",
                audit_citations=["Internal System Heuristic Validation Loop"]
            )

        # Tier 2: Critical Risk Path (T < 7.0 days) -> Escalation to Heavy Analytics
        print(
            f"🚨 CRITICAL COMPLIANCE TIMELINE DRIFT DETECTED ({predicted_t:.2f} Days)! Escalating to Heavy Reasoning Layer...")
        self.token_ledger["heavy_tier_calls"] += 1
        self.token_ledger["total_cost_usd"] += 0.0150

        if self.is_mock:
            return ComplianceAuditLog(
                risk_token="CRITICAL_BREACH",
                chain_of_thought=f"[MOCK ENGINE RUNTIME] Timeline collapsed to {predicted_t:.2f} days. Client has triggered material business model drift (Onboarding profile: SaaS -> Active: Crypto Trading) causing internal AML transaction limits to fracture.",
                audit_citations=["Swiss Corporate Registry (ZEFIX) Update Record", "Internal Transaction Ledger Match"]
            )

        # Secure Token-Constrained API Target Execution
        return self.instructor_client.chat.completions.create(
            model="gpt-4o-mini",  # Easily substituted with DeepSeek-R1 / local open-source models
            response_model=ComplianceAuditLog,
            messages=[
                {"role": "system",
                 "content": "You are AMINA Bank's Senior Compliance Automated Auditor. Analyze the payload against KYC baselines strictly."},
                {"role": "user", "content": f"Context Alert for Client {client_id}: {raw_payload}"}
            ]
        )


# --- QUICK COMPLIANCE CHECK LOOP ---
if __name__ == "__main__":
    print("Testing Step 5: Cost-Aware Router Integration...")
    router = CostAwareCascadingRouter()

    # Test nominal output routing
    print("\n--- Ingesting Safe System Output ---")
    safe_log = router.evaluate_routing_tier("CH-1002", predicted_t=25.98, raw_payload="Routine funding update.")
    print(f"Assigned Token: {safe_log.risk_token}\nRationale: {safe_log.chain_of_thought}")

    # Test high-risk threshold triggering (Simulating if T dropped to 3.5 days)
    print("\n--- Ingesting Crossed Threshold Alert ---")
    critical_log = router.evaluate_routing_tier("CH-4491", predicted_t=3.50,
                                                raw_payload="Company shifted headquarters offshore.")
    print(f"Assigned Token: {critical_log.risk_token}")
    print(f"Audit Rationale: {critical_log.chain_of_thought}")
    print(f"Verifiable Sources: {critical_log.audit_citations}")
    print(f"\nLive Budget Tracker: {router.token_ledger}")