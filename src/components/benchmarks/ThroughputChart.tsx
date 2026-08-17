export function ThroughputChart() {
  return (
    <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 flex flex-col h-full shadow-lg">
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-white">
          Throughput Comparison
        </h3>
        <p className="text-xs font-mono text-neutral-400 mt-0.5">
          Effective tokens per second (avg).
        </p>
      </div>

      <div className="flex-1 flex items-end justify-around pb-4 border-b border-[#262626] px-4 min-h-[140px]">
        {/* Raw Model */}
        <div className="flex flex-col items-center gap-2 group w-1/4">
          <div className="w-full bg-[#262626] rounded-t-md h-[30%] group-hover:bg-[#333333] transition-all" />
          <span className="text-[11px] text-neutral-500 font-mono mt-2">Raw</span>
        </div>

        {/* RE:Track */}
        <div className="flex flex-col items-center gap-2 group w-1/4">
          <div className="w-full bg-white rounded-t-md h-[85%] shadow-lg group-hover:bg-neutral-200 transition-all" />
          <span className="text-[11px] text-white font-mono mt-2 font-bold">
            RE:Track
          </span>
        </div>
      </div>

      <div className="mt-4 flex justify-center gap-6">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 bg-[#262626] rounded-sm" />
          <span className="text-xs font-mono text-neutral-500">
            Raw Baseline
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 bg-white rounded-sm" />
          <span className="text-xs font-mono text-neutral-300">
            RE:Track
          </span>
        </div>
      </div>
    </div>
  );
}
