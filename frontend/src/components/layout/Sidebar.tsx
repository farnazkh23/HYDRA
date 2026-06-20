import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { LayoutDashboard, Users, Bell, FileText, Terminal, Settings, ChevronRight, PieChart, BookOpen } from "lucide-react";
import { HydraLogo } from "@/components/HydraLogo";
import { getAlerts } from "@/lib/services";

type NavItem = {
  to: "/" | "/customers" | "/alerts" | "/reports" | "/logs" | "/settings" | "/portfolio" | "/documentation";
  label: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
  badge?: number;
};
const navBase: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/portfolio", label: "Portfolio", icon: PieChart },
  { to: "/customers", label: "Customers", icon: Users },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/logs", label: "Logs", icon: Terminal },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/documentation", label: "Documentation", icon: BookOpen },
];


export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [alertCount, setAlertCount] = useState<number | null>(null);

  useEffect(() => {
    getAlerts().then((a) => {
      const open = a.filter((x) => x.status === "open").length;
      setAlertCount(open > 0 ? open : null);
    }).catch(() => {});
  }, []);

  const nav = navBase.map((item) =>
    item.to === "/alerts" && alertCount ? { ...item, badge: alertCount } : item,
  );

  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar/80 backdrop-blur">
      <div className="px-6 pt-7 pb-8 flex items-center gap-3">
        <HydraLogo size={36} />
        <span className="font-display text-xl tracking-[0.2em] neon-text">HYDRA</span>
      </div>
      <nav className="flex-1 px-3 space-y-1">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-neon-soft text-neon"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              }`}
            >
              <Icon size={18} className={active ? "text-neon" : ""} />
              <span className="flex-1">{item.label}</span>
              {item.badge ? (
                <span className="rounded-full bg-[color:var(--risk-high)]/20 text-[color:var(--risk-high)] text-[10px] font-semibold px-2 py-0.5">
                  {item.badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <div className="m-3 mt-4 rounded-xl border border-sidebar-border bg-sidebar-accent/50 p-3 flex items-center gap-3">
        <div className="h-9 w-9 rounded-full bg-neon/20 grid place-items-center text-neon font-semibold text-sm">
          AR
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium truncate">Anna Rivera</div>
          <div className="text-[11px] text-muted-foreground truncate">Compliance Analyst</div>
        </div>
        <ChevronRight size={16} className="text-muted-foreground" />
      </div>
    </aside>
  );
}
