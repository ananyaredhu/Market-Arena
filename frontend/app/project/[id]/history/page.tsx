// OWNER: Person B. Decision history route.
import ProjectRoute, { type ProjectParams } from "@/components/layout/ProjectRoute";

import HistoryView from "./HistoryView";

export default function HistoryPage({ params }: { params: ProjectParams }) {
  return <ProjectRoute params={params} View={HistoryView} />;
}
