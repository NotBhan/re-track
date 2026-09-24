import React from "react";
import { NavLink } from "react-router-dom";
import { Code2, Compass, BrainCircuit, Settings2 } from "lucide-react";
import { cn } from "../../lib/utils";

export const NAVIGATION_ITEMS = [
  {
    to: "/code",
    label: "Code",
    description: "Repository AST & structure",
    icon: Code2,
  },
  {
    to: "/context",
    label: "Context",
    description: "Task synthesis & evidence",
    icon: Compass,
  },
  {
    to: "/memory",
    label: "Memory",
    description: "Derived semantic knowledge",
    icon: BrainCircuit,
  },
  {
    to: "/system",
    label: "System",
    description: "Providers, telemetry & diagnostics",
    icon: Settings2,
  },
];

export const Navigation: React.FC = () => {
  return (
    <aside className="w-56 bg-[#000000] border-r border-[#262626] p-2 flex flex-col justify-between select-none shrink-0">
      <nav className="flex flex-col gap-1">
        <div className="px-3 py-2 text-[10px] font-semibold text-[#707070] tracking-wider uppercase">
          Intelligence
        </div>
        {NAVIGATION_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors group",
                  isActive
                    ? "bg-[#121212] text-[#ededed] border border-[#262626]"
                    : "text-[#a1a1a1] hover:text-[#ededed] hover:bg-[#0a0a0a]"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn(
                      "w-4 h-4 transition-colors",
                      isActive ? "text-[#ededed]" : "text-[#707070] group-hover:text-[#a1a1a1]"
                    )}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-[#262626] flex items-center justify-between text-[11px] text-[#707070] font-mono">
        <span>RE:Track v0.1.0</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#121212] border border-[#262626] text-[#a1a1a1]">
          AST Grounded
        </span>
      </div>
    </aside>
  );
};
