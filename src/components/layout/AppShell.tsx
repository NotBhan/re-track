import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { useHealthPoll } from "@/hooks/use-health-poll";
import { LayoutProvider, useLayout } from "./LayoutContext";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: ReactNode;
  onNewIndex?: () => void;
}

function AppShellContent({ children, onNewIndex }: AppShellProps) {
  useHealthPoll(10000);
  const { mobileMenuOpen, closeMobileMenu } = useLayout();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-black text-foreground antialiased select-none">
      {/* Desktop Fixed Sidebar */}
      <Sidebar onNewIndex={onNewIndex} />

      {/* Mobile Drawer Overlay & Slide-over */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
            onClick={closeMobileMenu}
          />
          {/* Mobile Sidebar Content */}
          <div className="relative z-50 animate-in slide-in-from-left duration-200">
            <Sidebar
              onNewIndex={onNewIndex}
              onCloseMobile={closeMobileMenu}
              isMobile={true}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div
        className={cn(
          "w-full flex-1 flex flex-col h-screen overflow-hidden transition-all duration-200",
          "lg:ml-[260px]"
        )}
      >
        {children}
      </div>
    </div>
  );
}

export function AppShell(props: AppShellProps) {
  return (
    <LayoutProvider>
      <AppShellContent {...props} />
    </LayoutProvider>
  );
}
