import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Radio, ShieldCheck } from "lucide-react";
import { NAV_GROUPS } from "@/components/layout/nav-config";
import { cn } from "@/lib/utils";
import { useAppState } from "@/state/app-state";

export function Sidebar() {
  const { repository } = useAppState();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav aria-label="Primary" className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {group.label}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-primary/15 font-medium text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    )
                  }
                >
                  <item.icon className="size-4" aria-hidden="true" />
                  <span className="truncate">{item.label}</span>
                  {item.needsRepository && !repository && (
                    <span className="ml-auto size-1.5 rounded-full bg-warning" title="Select a repository first" />
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <>
      <button
        type="button"
        className="fixed left-3 top-3 z-40 rounded-md border border-border bg-card px-2.5 py-1.5 text-sm md:hidden"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls="sidebar"
      >
        Menu
      </button>
      {open && <div className="fixed inset-0 z-30 bg-black/50 md:hidden" onClick={() => setOpen(false)} aria-hidden="true" />}
      <aside
        id="sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform md:static md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2.5 border-b border-sidebar-border px-5 py-4">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <ShieldCheck className="size-5" aria-hidden="true" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-bold tracking-wide">USERSTORYAI</p>
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Radio className="size-3" aria-hidden="true" /> Repository intelligence
            </p>
          </div>
        </div>
        {nav}
        <p className="border-t border-sidebar-border px-5 py-3 text-[11px] text-muted-foreground">Version 0.4.0</p>
      </aside>
    </>
  );
}
