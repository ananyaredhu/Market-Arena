// Shared colour maps. Segment ids come from the data (packs/*.yaml, fixtures); add new ones here.
// Hex values mirror the tokens in app/globals.css (used where a colour is needed in JS, e.g. SVG/inline style).

export const COLORS = {
  accent: "#C8F560",
  blue: "#6B9BFF",
  teal: "#34D3BE",
  coral: "#FF7A6B",
  amber: "#F6B93B",
  violet: "#A98BFF",
  slate: "#7C8DB0",
} as const;

export type SegmentStyle = { label: string; color: string };

/** Segment id -> display name and dot colour. Unknown segments fall back to slate. */
export const SEGMENTS: Record<string, SegmentStyle> = {
  budget: { label: "Budget students", color: COLORS.coral },
  exam: { label: "Exam-focused students", color: COLORS.amber },
  power: { label: "Power planners", color: COLORS.teal },
  busy: { label: "Busy professionals", color: COLORS.amber },
  loyal: { label: "Skeptics (hostile)", color: COLORS.violet },
  skeptic: { label: "Skeptics (hostile)", color: COLORS.violet },
};

export const segmentStyle = (id: string): SegmentStyle =>
  SEGMENTS[id] ?? { label: id, color: COLORS.slate };

export type OptionStyle = { label: string; color: string; dashed?: boolean };

/** Option id -> label and ring colour. "you" is always the accent colour; the outside option is dashed. */
export const OPTION_STYLES: Record<string, OptionStyle> = {
  you: { label: "StudyFlow (you)", color: COLORS.accent },
  free_tool: { label: "FreeTool", color: COLORS.slate },
  chain_app: { label: "ChainApp", color: COLORS.slate },
  notebook_app: { label: "NotebookApp", color: COLORS.slate },
  outside: { label: "Do nothing", color: COLORS.slate, dashed: true },
};

export const optionStyle = (id: string): OptionStyle =>
  OPTION_STYLES[id] ?? { label: id, color: COLORS.slate };
