/** Join class names, skipping falsy values. */
export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

export type Tone = "accent" | "blue" | "teal" | "coral" | "amber" | "violet" | "muted";

// Static maps so Tailwind can see every class name.
export const TEXT_TONE: Record<Tone, string> = {
  accent: "text-accent",
  blue: "text-blue",
  teal: "text-teal",
  coral: "text-coral",
  amber: "text-amber",
  violet: "text-violet",
  muted: "text-muted",
};

export const BG_TONE: Record<Tone, string> = {
  accent: "bg-accent",
  blue: "bg-blue",
  teal: "bg-teal",
  coral: "bg-coral",
  amber: "bg-amber",
  violet: "bg-violet",
  muted: "bg-slate",
};
