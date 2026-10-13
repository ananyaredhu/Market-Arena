/** Concentric-rings mark plus wordmark. */
export default function Logo({ size = 28, wordmark = true }: { size?: number; wordmark?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
        <circle cx="14" cy="14" r="12" fill="none" stroke="#C8F560" strokeWidth="2" />
        <circle cx="14" cy="14" r="6" fill="none" stroke="#6B7A99" strokeWidth="2" />
        <circle cx="14" cy="14" r="2" fill="#C8F560" />
      </svg>
      {wordmark && <span className="font-display text-xl font-bold tracking-[-0.01em]">Market Arena</span>}
    </div>
  );
}
