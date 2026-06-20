// Data adapter layer. Toggle MODE between "mock" and "live".
import {
  alerts,
  customers,
  governance,
  graphEdges,
  graphNodes,
  kycDrift,
  reasoningTraces,
  engineLogs,
} from "./mock-data";
import type { Alert, Customer, GraphEdge, GraphNode } from "./types";

const MODE: "mock" | "live" = "live";

async function mockOk<T>(data: T): Promise<T> {
  return data;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export async function getCustomers(): Promise<Customer[]> {
  if (MODE === "mock") return mockOk(customers);
  return apiFetch<Customer[]>("/api/customers");
}

export async function getCustomerById(id: string): Promise<Customer | undefined> {
  if (MODE === "mock") return mockOk(customers.find((c) => c.id === id));
  return apiFetch<Customer>(`/api/customers/${id}`);
}

export async function getAlerts(): Promise<Alert[]> {
  if (MODE === "mock") return mockOk(alerts);
  return apiFetch<Alert[]>("/api/alerts");
}

export async function getAlertById(id: string) {
  if (MODE === "mock") return mockOk(alerts.find((a) => a.id === id));
  return apiFetch(`/api/alerts/${id}`);
}

export async function getGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  if (MODE === "mock") return mockOk({ nodes: graphNodes, edges: graphEdges });
  return apiFetch("/api/graph");
}

export async function getReasoningTrace(alertId: string) {
  if (MODE === "mock") return mockOk(reasoningTraces[alertId] ?? reasoningTraces["alert_001"]);
  return apiFetch(`/api/alerts/${alertId}/trace`);
}

export async function getKYCDriftRecord(customerId: string) {
  if (MODE === "mock") return mockOk(kycDrift[customerId]);
  return apiFetch(`/api/customers/${customerId}/kyc-drift`);
}

export async function getGovernanceRecord(alertId: string) {
  if (MODE === "mock") return mockOk(governance[alertId]);
  return apiFetch(`/api/alerts/${alertId}/governance`);
}

export async function getLogs() {
  if (MODE === "mock") return mockOk(engineLogs);
  return apiFetch("/api/logs");
}

export async function postAlertAction(alertId: string, action: "approve" | "escalate" | "dismiss", note = "") {
  if (MODE === "mock") return mockOk({ success: true });
  const res = await fetch(`/api/alerts/${alertId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note, actor: "compliance_officer" }),
  });
  if (!res.ok) throw new Error(`Action failed: ${res.status}`);
  return res.json();
}

export async function triggerPipeline(clientId: string, live = false) {
  if (MODE === "mock") return mockOk({ status: "ok" });
  const res = await fetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, live }),
  });
  if (!res.ok) throw new Error(`Pipeline trigger failed: ${res.status}`);
  return res.json();
}
