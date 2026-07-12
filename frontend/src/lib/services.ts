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

const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${path}`);
  }

  return response.json();
}

function unwrapList<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[];

  if (
    data &&
    typeof data === "object" &&
    "value" in data &&
    Array.isArray((data as { value?: unknown }).value)
  ) {
    return (data as { value: T[] }).value;
  }

  return [];
}

async function liveOrMock<T>(path: string, fallback: T): Promise<T> {
  try {
    return await fetchJson<T>(path);
  } catch (error) {
    console.warn(`Using mock fallback for ${path}`, error);
    return fallback;
  }
}

export async function getCustomers(): Promise<Customer[]> {
  try {
    const data = await fetchJson<unknown>("/customers");
    return unwrapList<Customer>(data);
  } catch (error) {
    console.warn("Using mock customers fallback", error);
    return customers;
  }
}

export async function getCustomerById(id: string): Promise<Customer | undefined> {
  return liveOrMock<Customer | undefined>(
    `/customers/${id}`,
    customers.find((customer) => customer.id === id),
  );
}

export async function getAlerts(): Promise<Alert[]> {
  try {
    const data = await fetchJson<unknown>("/alerts");
    return unwrapList<Alert>(data);
  } catch (error) {
    console.warn("Using mock alerts fallback", error);
    return alerts;
  }
}

export async function getAlertById(id: string): Promise<Alert | undefined> {
  return liveOrMock<Alert | undefined>(
    `/alerts/${id}`,
    alerts.find((alert) => alert.id === id),
  );
}

export async function getGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  return liveOrMock<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
    "/graph",
    { nodes: graphNodes, edges: graphEdges },
  );
}

export async function getReasoningTrace(alertId: string) {
  return liveOrMock(
    `/alerts/${alertId}/trace`,
    reasoningTraces[alertId] ?? reasoningTraces["alert_001"],
  );
}

export async function getKYCDriftRecord(customerId: string) {
  return liveOrMock(
    `/customers/${customerId}/kyc-drift`,
    kycDrift[customerId],
  );
}

export async function getGovernanceRecord(alertId: string) {
  return liveOrMock(
    `/alerts/${alertId}/governance`,
    governance[alertId],
  );
}

export async function getLogs() {
  return liveOrMock("/logs", engineLogs);
}
