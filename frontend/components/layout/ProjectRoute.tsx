import { type ComponentType, Suspense, use } from "react";

export type ProjectParams = Promise<{ id: string }>;

/**
 * Wrapper for every /project/[id]/... page. This Next.js version needs runtime params to be read inside
 * <Suspense>, so a route file stays a thin server component and the real page is a client "View":
 *
 *   // app/project/[id]/thing/page.tsx
 *   import ProjectRoute, { type ProjectParams } from "@/components/layout/ProjectRoute";
 *   import ThingView from "./ThingView";
 *   export default function Page({ params }: { params: ProjectParams }) {
 *     return <ProjectRoute params={params} View={ThingView} />;
 *   }
 *
 *   // ThingView.tsx starts with "use client" and does: const { id } = use(params);
 */
export default function ProjectRoute({
  params,
  View,
}: {
  params: ProjectParams;
  View: ComponentType<{ params: ProjectParams }>;
}) {
  return (
    <Suspense fallback={<main className="p-8 text-muted">Loading…</main>}>
      <ProjectScopedView params={params} View={View} />
    </Suspense>
  );
}

function ProjectScopedView({ params, View }: { params: ProjectParams; View: ComponentType<{ params: ProjectParams }> }) {
  const { id } = use(params);
  // A project change discards local selection and pending UI state in every view.
  return <View key={id} params={params} />;
}
