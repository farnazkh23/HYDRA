import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/alerts")({
  head: () => ({ meta: [{ title: "Alerts — HYDRA" }] }),
  component: Outlet,
});
