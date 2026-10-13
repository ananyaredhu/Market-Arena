// OWNER: Person C. Screen 1 route. See ProjectRoute for why this is a thin wrapper.
import ProjectRoute, { type ProjectParams } from "@/components/layout/ProjectRoute";

import ProjectView from "./ProjectView";

export default function ProjectPage({ params }: { params: ProjectParams }) {
  return <ProjectRoute params={params} View={ProjectView} />;
}
