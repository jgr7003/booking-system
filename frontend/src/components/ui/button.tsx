import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const VARIANTS = {
  primary: "bg-action text-white hover:bg-action-hover disabled:bg-subtle",
  secondary: "border border-line bg-white text-ink hover:border-subtle disabled:text-subtle",
  ghost: "text-action hover:bg-action-soft disabled:text-subtle",
  danger: "text-bad hover:bg-bad-soft",
} as const;

const SIZES = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-10 px-4",
  lg: "h-12 px-6 text-[15px]",
} as const;

export type ButtonVariant = keyof typeof VARIANTS;

/** Class names of a button, also used to style links as buttons. */
export function buttonClass(
  variant: ButtonVariant = "primary",
  size: keyof typeof SIZES = "md",
  className?: string,
) {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-colors",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action disabled:cursor-not-allowed",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: keyof typeof SIZES;
}

export function Button({ variant, size, className, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, size, className)} {...props} />;
}
