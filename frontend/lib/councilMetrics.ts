// Display helpers. Shares stay fractions until formatted. Missing numbers stay null.
import type { CouncilOutput } from "@/lib/types";

export const MEDIAN_SHARE = /median share of (\d+(?:\.\d+)?)/;
export const SHARE_MOVE = /share (\d+(?:\.\d+)?) -> (\d+(?:\.\d+)?)/;
export const SEGMENT_LINE = /^([^:]+): (\d+) of (\d+) simulated agents chose .+ \((\d+(?:\.\d+)?)\)/;

export function formatShare(share: number): string {
  return `${Math.round(share * 1000) / 10}%`;
}

export interface ParsedSegment {
  name: string;
  nYou: number;
  n: number;
  share: number;
}

export function parseSegmentLine(line: string): ParsedSegment | null {
  const match = line.match(SEGMENT_LINE);
  if (!match) return null;
  return {
    name: match[1],
    nYou: Number(match[2]),
    n: Number(match[3]),
    share: Number(match[4]),
  };
}

export function parseShareMove(metric: string): { before: number; after: number } | null {
  const match = metric.match(SHARE_MOVE);
  if (!match) return null;
  return { before: Number(match[1]), after: Number(match[2]) };
}

export function medianShare(council: CouncilOutput): number | null {
  if (council.measured?.median_share != null) return council.measured.median_share;
  const match = council.verdict.match(MEDIAN_SHARE);
  return match ? Number(match[1]) : null;
}

export function baselineShare(council: CouncilOutput): number | null {
  if (council.measured?.baseline_share != null) return council.measured.baseline_share;
  return medianShare(council);
}
