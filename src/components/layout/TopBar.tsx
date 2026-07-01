import { Bell, User } from "lucide-react";
import { IconButton } from "@/components/shared/IconButton";

interface TopBarProps {
  title?: string;
  children?: React.ReactNode;
}

export function TopBar({ title, children }: TopBarProps) {
  return (
    <header className="h-16 w-full sticky top-0 z-10 bg-surface flex items-center justify-between px-4 border-b border-outline-variant/30">
      <div className="flex items-center gap-4 flex-1">
        {title && (
          <h2 className="text-[16px] leading-[24px] font-semibold text-primary">
            {title}
          </h2>
        )}
        {children}
      </div>
      <div className="flex items-center gap-2">
        <IconButton icon={Bell} label="Notifications" />
        <IconButton icon={User} label="Account" />
      </div>
    </header>
  );
}
