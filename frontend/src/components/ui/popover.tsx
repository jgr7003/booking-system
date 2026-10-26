import { Popover as RadixPopover } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "@/lib/cn";

export const Popover = RadixPopover.Root;
export const PopoverTrigger = RadixPopover.Trigger;
export const PopoverAnchor = RadixPopover.Anchor;
export const PopoverClose = RadixPopover.Close;

export function PopoverContent({
  className,
  align = "start",
  ...props
}: ComponentProps<typeof RadixPopover.Content>) {
  return (
    <RadixPopover.Portal>
      <RadixPopover.Content
        align={align}
        sideOffset={6}
        collisionPadding={16}
        className={cn(
          "z-40 w-[min(360px,calc(100vw-32px))] rounded-lg border border-line bg-white p-4 shadow-lg",
          className,
        )}
        {...props}
      />
    </RadixPopover.Portal>
  );
}
