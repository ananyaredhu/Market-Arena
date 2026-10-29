// OWNER: Person A. One entry of the Resources library: what a web page said, the exact words, and where to check it.
import { Card, Pill } from "@/components/ui";
import type { Resource } from "@/lib/types";

export const retrieved = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
};

export default function ResourceCard({ r }: { r: Resource }) {
  return (
    <Card className="flex flex-col gap-3 !p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Pill variant="idle" className="!px-3 !py-1 !text-xs">{r.topic}</Pill>
        <span className="font-mono text-xs text-muted">
          {r.pack} · {r.geography}
        </span>
      </div>
      <p className="m-0 text-base leading-normal">{r.claim}</p>
      <Card variant="inset" className="!px-4 !py-3">
        <blockquote className="m-0 border-l-2 border-line-3 pl-3 text-sm italic leading-normal text-ink-soft">
          “{r.quote}”
        </blockquote>
      </Card>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <a href={r.url} target="_blank" rel="noopener noreferrer" className="break-all text-blue underline-offset-2 hover:underline">
          {r.domain}
        </a>
        <span>retrieved {retrieved(r.retrieved_at)}</span>
        <span>quote checked against the page</span>
      </div>
    </Card>
  );
}
