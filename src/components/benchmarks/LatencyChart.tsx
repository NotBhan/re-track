export function LatencyChart() {
  return (
    <div className="bg-[#0a0a0a] border border-[#262626] rounded-xl p-5 flex flex-col relative overflow-hidden h-full shadow-lg">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-sm font-semibold text-white">
            Generation Latency
          </h3>
          <p className="text-xs font-mono text-neutral-400 mt-0.5">
            Rolling average over last benchmark execution.
          </p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-white rounded-full" />
            <span className="text-xs font-mono text-neutral-300">
              RE:Track
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-[#404040] rounded-full" />
            <span className="text-xs font-mono text-neutral-500">
              Raw Model
            </span>
          </div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="flex-1 relative border-l border-b border-[#262626] mt-2 mx-4 mb-4 min-h-[160px]">
        {/* Y Axis */}
        <div className="absolute -left-10 top-0 h-full flex flex-col justify-between text-[10px] text-neutral-500 font-mono py-1">
          <span>800ms</span>
          <span>600ms</span>
          <span>400ms</span>
          <span>200ms</span>
          <span>0ms</span>
        </div>

        {/* X Axis */}
        <div className="absolute -bottom-6 left-0 w-full flex justify-between text-[10px] text-neutral-500 font-mono px-1">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>Now</span>
        </div>

        {/* SVG Lines */}
        <svg
          className="absolute inset-0 w-full h-full overflow-visible"
          preserveAspectRatio="none"
          viewBox="0 0 100 100"
        >
          {/* Raw Model Line (muted dashed) */}
          <path
            d="M 0,40 Q 10,45 20,30 T 40,50 T 60,35 T 80,45 T 100,20"
            fill="none"
            stroke="#404040"
            strokeDasharray="4 2"
            strokeWidth="1.5"
          />

          {/* RE:Track Line (white) */}
          <path
            d="M 0,70 Q 15,65 30,75 T 50,60 T 70,80 T 90,65 T 100,75"
            fill="none"
            stroke="#ffffff"
            strokeWidth="2"
          />

          {/* Data Point */}
          <circle
            cx="100"
            cy="75"
            fill="#ffffff"
            r="3"
          />
        </svg>
      </div>
    </div>
  );
}
