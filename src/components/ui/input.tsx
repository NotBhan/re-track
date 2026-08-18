import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-8.5 w-full min-w-0 rounded-md border border-[#222222] bg-[#050505] px-3 py-1.5 text-xs text-neutral-200 shadow-xs transition-colors outline-none placeholder:text-neutral-600 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40 focus-visible:border-neutral-400 focus-visible:ring-1 focus-visible:ring-neutral-400",
        className
      )}
      {...props}
    />
  )
}

export { Input }
