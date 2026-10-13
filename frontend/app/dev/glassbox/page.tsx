"use client";
// Standalone page so Person A can build the Glass-Box drawer without anyone else's code.
import GlassBoxDrawer from "@/components/glassbox/GlassBoxDrawer";

export default function DevGlassBox() {
  return (
    <main className="mx-auto min-h-screen w-[380px] max-w-full">
      <GlassBoxDrawer agentId="a055" runId="run_42" onOverride={() => console.log("override")} />
    </main>
  );
}
