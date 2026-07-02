import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { useHealthPoll } from "@/hooks/use-health-poll";

interface AppShellProps {
  children: ReactNode;
  onNewIndex?: () => void;
}

export function AppShell({ children, onNewIndex }: AppShellProps) {
  useHealthPoll(10000);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar onNewIndex={onNewIndex} />
      <div className="ml-[240px] flex-1 flex flex-col h-full overflow-hidden">
        {children}
      </div>
    </div>
  );
}
