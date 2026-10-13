"use client";
// OWNER: Person B. "Landing page draft": a light-themed preview of the generated copy plus the other assets.
import { Button, Card, Pill, SectionLabel } from "@/components/ui";
import type { KitOutput } from "@/lib/types";

export default function LandingPreview({
  headline,
  body,
  ctas,
  assets,
}: {
  headline: string;
  body: string;
  ctas: [string, string];
  assets: KitOutput["assets"];
}) {
  const alsoGenerated = [
    `${assets.survey.length}-question survey`,
    "Interview script",
    `${assets.ad_variants.length} ad variants`,
    "Tracking sheet",
  ];
  return (
    <Card className="flex min-w-0 flex-[1_1_400px] flex-col gap-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <SectionLabel>Landing page draft</SectionLabel>
        <Button onClick={() => navigator.clipboard?.writeText(`${headline}\n\n${body}`)}>Copy</Button>
      </div>
      {/* The preview is intentionally light: it shows what the founder's visitors will see. */}
      <div className="flex flex-col gap-3 rounded-2xl bg-[#f6f3ea] p-7 text-[#14161c]">
        <div className="font-display text-[30px] font-bold leading-[1.1]">{headline}</div>
        <div className="text-[15px] leading-normal text-[#3a3f4b]">{body}</div>
        <div className="flex flex-wrap gap-2.5">
          <span className="rounded-[10px] bg-[#14161c] px-4 py-2.5 text-sm font-bold text-white">{ctas[0]}</span>
          <span className="rounded-[10px] border border-[#14161c] px-4 py-2.5 text-sm">{ctas[1]}</span>
        </div>
      </div>
      <SectionLabel className="mt-1">Also generated</SectionLabel>
      <div className="flex flex-wrap gap-2">
        {alsoGenerated.map((a) => (
          <Pill key={a} variant="outline" className="px-3 py-1.5">{a}</Pill>
        ))}
      </div>
    </Card>
  );
}
