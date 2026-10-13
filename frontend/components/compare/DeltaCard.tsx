// OWNER: Person A. The lime "+10 pts" headline between the two scenarios.
export default function DeltaCard({ value, caption, range }: { value: string; caption: string; range?: string }) {
  return (
    <div className="flex flex-[0_0_260px] flex-col justify-center rounded-[20px] bg-accent p-[22px] text-bg">
      <div className="font-mono text-[44px] font-medium leading-none">{value}</div>
      <div className="mt-2 text-sm font-bold">{caption}</div>
      {range && <div className="mt-0.5 text-[13px]">{range}</div>}
    </div>
  );
}
