/** Shared identity and request guards used by the real console and its tests. */
export type CampaignScope = { projectId: string; runId: string };
export type CampaignIdentity = { id: string; project_id: string; run_id: string };

export function campaignPath(scope: CampaignScope, id: string, operation: string) {
  const query = new URLSearchParams({ project_id: scope.projectId, run_id: scope.runId });
  return `/telegram/campaigns/${encodeURIComponent(id)}/${operation}?${query}`;
}

export function assertCampaignIdentity(scope: CampaignScope, id: string, data: CampaignIdentity) {
  if (data.id !== id || data.project_id !== scope.projectId || data.run_id !== scope.runId) {
    throw new Error("Campaign response does not belong to the displayed project, run and campaign.");
  }
}

export class CampaignRequestGate {
  private revision = 0;
  private pending = false;
  begin(): number | null {
    if (this.pending) return null;
    this.pending = true;
    return ++this.revision;
  }
  current(ticket: number) { return this.pending && ticket === this.revision; }
  finish(ticket: number) {
    if (!this.current(ticket)) return false;
    this.pending = false;
    return true;
  }
  invalidate() { this.revision++; this.pending = false; }
}
