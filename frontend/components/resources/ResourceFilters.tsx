"use client";
// OWNER: Person A. Pack, topic and text filters for the Resources library.
import { Pill, SectionLabel } from "@/components/ui";

const chip = "cursor-pointer rounded-full";

export default function ResourceFilters({
  packs,
  pack,
  onPack,
  topics,
  topic,
  onTopic,
  query,
  onQuery,
}: {
  packs: string[];
  pack: string;
  onPack: (v: string) => void;
  topics: Record<string, number>;
  topic: string;
  onTopic: (v: string) => void;
  query: string;
  onQuery: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-x-8 gap-y-4">
      <div className="flex flex-col gap-1.5">
        <SectionLabel>Industry pack</SectionLabel>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Industry pack">
          {["", ...packs].map((p) => (
            <button key={p || "all"} type="button" className={chip} aria-pressed={pack === p} onClick={() => onPack(p)}>
              <Pill variant={pack === p ? "active" : "idle"}>{p || "all"}</Pill>
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <SectionLabel>Topic</SectionLabel>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Topic">
          {["", ...Object.keys(topics)].map((t) => (
            <button key={t || "all"} type="button" className={chip} aria-pressed={topic === t} onClick={() => onTopic(t)}>
              <Pill variant={topic === t ? "active" : "idle"}>
                {t || "all"}
                {t ? ` · ${topics[t]}` : ""}
              </Pill>
            </button>
          ))}
        </div>
      </div>
      <label className="flex flex-col gap-1.5">
        <SectionLabel>Search</SectionLabel>
        <input
          aria-label="Search resources"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="words in a claim, quote or website"
          className="min-h-11 w-72 rounded-lg border border-line-3 bg-bg px-3 text-ink"
        />
      </label>
    </div>
  );
}
