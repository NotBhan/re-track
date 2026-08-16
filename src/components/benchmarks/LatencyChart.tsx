export function LatencyChart() {
  return (
    <div className="bg-surface-container-low border border-outline-variant/50 rounded-xl p-5 flex flex-col relative overflow-hidden h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-[16px] leading-[24px] font-semibold text-on-surface">
            Generation Latency
          </h3>
          <p className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant mt-1">
            Rolling average over last 24 hours.
          </p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-primary rounded-full" />
            <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
              RE:Track
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-outline rounded-full" />
            <span className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface-variant">
              Raw Model
            </span>
          </div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="flex-1 relative chart-grid border-l border-b border-surface-variant mt-2 mx-4 mb-4">
        {/* Y Axis */}
        <div className="absolute -left-10 top-0 h-full flex flex-col justify-between text-[10px] text-outline font-mono py-1">
          <span>800ms</span>
          <span>600ms</span>
          <span>400ms</span>
          <span>200ms</span>
          <span>0ms</span>
        </div>

        {/* X Axis */}
        <div className="absolute -bottom-6 left-0 w-full flex justify-between text-[10px] text-outline font-mono px-1">
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
            stroke="#424754"
            strokeDasharray="4 2"
            strokeWidth="1.5"
          />

          {/* RE:Track Line (primary) */}
          <path
            className="drop-shadow-[0_4px_6px_rgba(173,198,255,0.2)]"
            d="M 0,70 Q 15,65 30,75 T 50,60 T 70,80 T 90,65 T 100,75"
            fill="none"
            stroke="#adc6ff"
            strokeWidth="2"
          />

          {/* Gradient Area */}
          <path
            d="M 0,70 Q 15,65 30,75 T 50,60 T 70,80 T 90,65 T 100,75 L 100,100 L 0,100 Z"
            fill="url(#primaryGradient)"
            opacity="0.1"
          />
          <defs>
            <linearGradient
              id="primaryGradient"
              x1="0%"
              x2="0%"
              y1="0%"
              y2="100%"
            >
              <stop offset="0%" stopColor="#adc6ff" />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>

          {/* Data Point */}
          <circle
            className="animate-pulse"
            cx="100"
            cy="75"
            fill="#adc6ff"
            r="3"
          />
        </svg>
      </div>
    </div>
  );
}
