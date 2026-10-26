/** Replace only the obsolete integration notice, leaving experiment advice untouched. */
const LEGACY_NOTICE = "Telegram delivery, approval and measured click rates are not live. Variant text comes from this kit.";
export function kitPresentationNotices(notices: string[] = []) {
  return notices.filter(notice => notice.trim() !== LEGACY_NOTICE);
}

export type BackendState = "checking" | "offline" | "mock" | "real";
export type DeliveryState = "unverified" | "unconfigured" | "confirmed";
export function telegramAvailability(backend: BackendState, delivery: DeliveryState) {
  if (backend === "checking") return "Checking the backend. Real Telegram mode is selected; delivery is not yet verified.";
  if (backend === "offline") return "Backend unavailable. This local console cannot create or send campaigns while offline.";
  if (backend === "mock") return "The backend is in mock mode. Delivery is simulated; use backend MOCK=0 for real campaign management.";
  if (delivery === "unconfigured") return "Server configuration is incomplete. Real delivery is unavailable until the required credentials are configured.";
  if (delivery === "confirmed") return "Real Telegram delivery was confirmed by a successful send in this campaign. Engagement below is observed, not simulated.";
  return "Backend connected in real mode. Bot delivery configuration is not yet verified. Campaign creation and approval alone do not confirm delivery readiness.";
}
