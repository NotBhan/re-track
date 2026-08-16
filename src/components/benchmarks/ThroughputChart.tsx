export function ThroughputChart() {
  return (
    <div className="bg-surface-container-low border border-outline-variant/50 rounded-xl p-5 flex flex-col h-full">
      <div className="mb-6">
        <h3 className="text-[16px] leading-[24px] font-semibold text-on-surface">
          Throughput Compare
        </h3>
        <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mt-1">
          Tokens per second (avg).
        </p>
      </div>

      <div className="flex-1 flex items-end justify-around pb-4 border-b border-surface-variant chart-grid px-4">
        {/* Cognee Default */}
        <div className="flex flex-col items-center gap-2 group w-1/4">
          <div className="w-full bg-surface-variant rounded-t-sm h-[30%] hover:brightness-110 transition-all" />
          <span className="text-[10px] text-outline font-mono mt-2">Raw</span>
        </div>

        {/* RE:Track */}
        <div className="flex flex-col items-center gap-2 group w-1/4">
          <div className="w-full bg-primary rounded-t-sm h-[85%] shadow-[0_0_10px_rgba(173,198,255,0.1)] hover:brightness-110 transition-all" />
          <span className="text-[10px] text-primary font-mono mt-2">
            RE:Track
          </span>
        </div>
      </div>

      <div className="mt-4 flex justify-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-surface-variant rounded-sm" />
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            Cognee Default
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-primary rounded-sm" />
          <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
            RE:Track
          </span>
        </div>
      </div>
    </div>
  );
}
