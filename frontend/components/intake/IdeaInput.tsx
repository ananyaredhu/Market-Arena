"use client";
// OWNER: Person C. Idea textarea with the two actions. Wire onSubmit to POST /projects.
import { useState } from "react";

import { Button, SectionLabel } from "@/components/ui";

export default function IdeaInput({
  initial = "",
  onSubmit,
  onUseForm,
  disabled = false,
}: {
  initial?: string;
  onSubmit?: (text: string) => void;
  onUseForm?: () => void;
  disabled?: boolean;
}) {
  const [text, setText] = useState(initial);
  return (
    <>
      <label htmlFor="idea">
        <SectionLabel>Your idea</SectionLabel>
      </label>
      <textarea
        id="idea"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        className="min-h-[190px] flex-1 resize-none rounded-2xl border border-line-2 bg-surface-2 p-5 text-[17px] leading-[1.55] text-ink"
      />
      <div className="flex flex-wrap gap-2.5">
        <Button variant="primary" size="lg" disabled={disabled} onClick={() => onSubmit?.(text)}>
          {disabled ? "Building market…" : "Build my market →"}
        </Button>
        <Button size="lg" disabled={disabled} onClick={onUseForm}>
          Use the form instead
        </Button>
      </div>
    </>
  );
}
