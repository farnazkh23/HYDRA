// Data adapter layer. Currently reads from mock data; later switch to fetch().
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

const MODE: "mock" | "live" = "mock";

async function mockOk<T>(data: T): Promise<T> {
  return data;
}

export async function getCustomers(): Promise<Customer[]> {
  if (MODE === "mock") return mockOk(customers);
  return fetch("/api/customers").then((r) => r.json());
}

export async function getCustomerById(id: string): Promise<Customer | undefined> {
  if (MODE === "mock") return mockOk(customers.find((c) => c.id === id));
  return fetch(`/api/customers/${id}`).then((r) => r.json());
}

export async function getAlerts(): Promise<Alert[]> {
  return mockOk(alerts);
}

export async function getAlertById(id: string) {
  return mockOk(alerts.find((a) => a.id === id));
}

export async function getGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  return mockOk({ nodes: graphNodes, edges: graphEdges });
}

export async function getReasoningTrace(alertId: string) {
  return mockOk(reasoningTraces[alertId] ?? reasoningTraces["alert_001"]);
}

export async function getKYCDriftRecord(customerId: string) {
  return mockOk(kycDrift[customerId]);
}

export async function getGovernanceRecord(alertId: string) {
  return mockOk(governance[alertId]);
}

export async function getLogs() {
  return mockOk(engineLogs);
}
