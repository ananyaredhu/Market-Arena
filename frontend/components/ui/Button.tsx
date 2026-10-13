import type { ButtonHTMLAttributes } from "react";

import { cx } from "@/lib/cx";

const VARIANTS = {
  primary: "bg-accent text-bg font-bold border-0",
  secondary: "bg-transparent text-ink border border-line-3",
  warn: "bg-transparent text-warn-ink border border-warn-line",
} as const;

const SIZES = {
  md: "min-h-11 px-[18px] text-sm rounded-[10px]",
  lg: "min-h-12 px-6 text-base rounded-xl",
} as const;

export default function Button({
  variant = "secondary",
  size = "md",
  className,
  ...rest
}: {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cx(VARIANTS[variant], SIZES[size], className)} {...rest} />;
}
