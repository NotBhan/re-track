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
    <div className="flex h-screen w-screen overflow-hidden bg-black text-foreground">
      <Sidebar onNewIndex={onNewIndex} />
      <div className="ml-[260px] flex-1 flex flex-col h-screen overflow-hidden">
        {children}
      </div>
    </div>
  );
}
