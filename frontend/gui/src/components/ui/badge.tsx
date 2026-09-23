import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-none whitespace-nowrap transition-colors focus-visible:outline-none [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-white text-black",
        secondary:
          "border-[#262626] bg-[#141414] text-neutral-300",
        destructive:
          "border-red-500/30 bg-red-950/20 text-red-400",
        outline:
          "border-[#222222] bg-[#0c0c0c] text-neutral-300",
        ghost:
          "border-transparent text-neutral-400 hover:text-white",
        success:
          "border-emerald-500/30 bg-emerald-950/20 text-emerald-400",
        warning:
          "border-amber-500/30 bg-amber-950/20 text-amber-400",
        link:
          "border-transparent text-primary underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
