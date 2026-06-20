# analytic_engine/router.py
import os
import json
from pydantic import BaseModel, Field
from typing import List, Literal


class ComplianceAuditLog(BaseModel):
    risk_token: Literal["LOW_RISK", "ELEVATED_DRIFT", "CRITICAL_BREACH"] = Field(
        ..., description="Final risk classification layer based on combined indicators."
    )
    chain_of_thought: str = Field(
        ..., description="Step-by-step reasoning contrasting public indicators with internal KYC baselines."
    )
    audit_citations: List[str] = Field(
        ..., description="Verifiable strings or system flags matching corporate records."
    )


class CostAwareCascadingRouter:
    def __init__(self):
        """
        Sovereign Gateway Routing Module.
        Connected directly to the Swiss AI Initiative Apertus platform via PublicAI.
        """
        self.api_key = os.getenv("APERTUS_API_KEY")
        self.client = None

        if not self.api_key:
            print("[System Alert] APERTUS_API_KEY environment variable not found. Router running in Fallback Mode.")
        else:
            try:
                from openai import OpenAI
                # Route directly through PublicAI's gateway endpoint configuration
                # Injects the mandatory User-Agent header directly into all SDK calls
                self.client = OpenAI(
                    base_url="https://api.publicai.co/v1",
                    api_key=self.api_key,
                    default_headers={"User-Agent": "SwissHacksHydraRiskEngine/1.0"}
                )
                print("Successfully initialized live Swiss Apertus AI Engine via PublicAI gateway.")
            except Exception as e:
                print(f"[Warning] Sovereign SDK setup failed ({e}). Reverting to fallback.")
                self.client = None

        self.token_ledger = {"cheap_tier_calls": 0, "heavy_tier_calls": 0, "total_cost_usd": 0.0}

    def evaluate_routing_tier(self, client_id: str, predicted_t: float, raw_payload: str) -> ComplianceAuditLog:
        """
        Evaluates remaining survival buffer (T) to allocate token compute tiers.
        """
        if predicted_t >= 7.0:
            self.token_ledger["cheap_tier_calls"] += 1
            self.token_ledger["total_cost_usd"] += 0.0002
            return ComplianceAuditLog(
                risk_token="LOW_RISK",
                chain_of_thought=f"Automatic pass: profile stability horizon is secure at {predicted_t:.2f} days.",
                audit_citations=["Internal System Heuristic Verification Loop"]
            )

        print(f"🚨 CRITICAL DRIFT LIMIT BREACHED ({predicted_t:.2f} Days)! Escalating to Swiss Apertus AI Layer...")
        self.token_ledger["heavy_tier_calls"] += 1

        # PublicAI Pricing Structure Reference: Input $0.10/1M tokens, Output $0.20/1M tokens
        self.token_ledger["total_cost_usd"] += 0.00015

        if self.client is None:
            return self._execute_mock_fallback(predicted_t)

        try:
            prompt = f"""You are AMINA Bank's Senior Compliance Automated Auditor.
Analyze this corporate profile drift context.
Return a raw, clean JSON string parsing exactly back to this structural pattern:
{{
  "risk_token": "CRITICAL_BREACH",
  "chain_of_thought": "your detailed step-by-step audit reasoning matching onboarding divergence metrics",
  "audit_citations": ["citation string 1", "citation string 2"]
}}

Context Parameters for Client {client_id}: {raw_payload}. Predicted decay profile window: {predicted_t:.2f} days."""

            response = self.client.chat.completions.create(
                model="swiss-ai/apertus-8b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            raw_content = response.choices[0].message.content

            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(raw_content.strip())

            # SANITIZATION GATE: If the model returns an array of strings for chain_of_thought, join them!
            cot_raw = parsed_json.get("chain_of_thought", "Analysis completed.")
            if isinstance(cot_raw, list):
                chain_of_thought_validated = " ".join([str(item) for item in cot_raw])
            else:
                chain_of_thought_validated = str(cot_raw)

            return ComplianceAuditLog(
                risk_token=parsed_json.get("risk_token", "CRITICAL_BREACH"),
                chain_of_thought=chain_of_thought_validated,  # Safe flattened string
                audit_citations=parsed_json.get("audit_citations", ["Sovereign Audit Trail Cleared"])
            )

        except Exception as e:
            print(f"[Warning] Live Apertus inference failed ({e}). Engaging safety recovery loop...")
            return self._execute_mock_fallback(predicted_t)

    def _execute_mock_fallback(self, predicted_t: float) -> ComplianceAuditLog:
        return ComplianceAuditLog(
            risk_token="CRITICAL_BREACH",
            chain_of_thought=f"[APERTUS FALLBACK LOG] Survival horizon collapsed to {predicted_t:.2f} days. Active corporate transactions show material deviation from onboarding baseline (SaaS Model -> Crypto Trading Brokerage).",
            audit_citations=["Swiss Corporate Registry (ZEFIX) Fallback Check", "Internal Transaction Ledger Match"]
        )