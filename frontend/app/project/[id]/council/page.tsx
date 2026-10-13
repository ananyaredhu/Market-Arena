// OWNER: Person B. Screen 3 route.
import ProjectRoute, { type ProjectParams } from "@/components/layout/ProjectRoute";

import CouncilView from "./CouncilView";

export default function CouncilPage({ params }: { params: ProjectParams }) {
  return <ProjectRoute params={params} View={CouncilView} />;
}
