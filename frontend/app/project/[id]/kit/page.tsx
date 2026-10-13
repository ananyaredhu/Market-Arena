// OWNER: Person B (Kit) and Person C (Telegram). Screen 5 route.
import ProjectRoute, { type ProjectParams } from "@/components/layout/ProjectRoute";

import KitView from "./KitView";

export default function KitPage({ params }: { params: ProjectParams }) {
  return <ProjectRoute params={params} View={KitView} />;
}
