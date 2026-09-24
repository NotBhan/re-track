import React from "react";
import { useUiScaleStore, AVAILABLE_SCALES } from "../../stores/uiScaleStore";
import { Button } from "../../components/Button";
import { ZoomIn, ZoomOut, RotateCcw, Monitor } from "lucide-react";

export const DisplaySettings: React.FC = () => {
  const { scale, setScale, zoomIn, zoomOut, resetScale } = useUiScaleStore();

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[#262626]">
          <Monitor className="w-4 h-4 text-[#a1a1a1]" />
          <h4 className="text-xs font-semibold text-[#ededed] uppercase tracking-wider font-mono">
            User Interface Scale
          </h4>
        </div>

        <p className="text-xs text-[#a1a1a1] leading-relaxed">
          Control the overall zoom and interface density of the RE:Track desktop application.
          Changes are persisted automatically across application launches.
        </p>

        {/* Current Scale Display & Steppers */}
        <div className="flex items-center justify-between p-3 rounded-md bg-[#121212] border border-[#262626]">
          <div className="flex flex-col">
            <span className="text-xs font-medium text-[#ededed]">Current Scale</span>
            <span className="text-[11px] text-[#707070]">Zoom multiplier</span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={zoomOut}
              disabled={scale <= 80}
              title="Zoom Out (Ctrl -)"
            >
              <ZoomOut className="w-3.5 h-3.5 mr-1" />
              <span>Smaller</span>
            </Button>

            <span className="w-16 text-center font-mono text-sm font-semibold text-[#ededed] px-2 py-1 rounded bg-[#0a0a0a] border border-[#262626]">
              {scale}%
            </span>

            <Button
              size="sm"
              variant="secondary"
              onClick={zoomIn}
              disabled={scale >= 150}
              title="Zoom In (Ctrl +)"
            >
              <ZoomIn className="w-3.5 h-3.5 mr-1" />
              <span>Larger</span>
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={resetScale}
              title="Reset to 100% (Ctrl 0)"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Preset Scale Options */}
        <div className="flex flex-col gap-2 pt-2">
          <span className="text-[11px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
            Scale Presets
          </span>
          <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
            {AVAILABLE_SCALES.map((s) => (
              <button
                key={s}
                onClick={() => setScale(s)}
                className={`py-2 px-3 text-xs font-mono rounded-md border transition-colors ${
                  scale === s
                    ? "bg-[#ffffff] text-[#000000] border-[#ffffff] font-semibold"
                    : "bg-[#121212] text-[#a1a1a1] border-[#262626] hover:border-[#404040] hover:text-[#ededed]"
                }`}
              >
                {s}%
              </button>
            ))}
          </div>
        </div>

        {/* Keyboard Shortcuts Cheatsheet */}
        <div className="p-3 rounded-md bg-[#121212] border border-[#262626] flex flex-col gap-2 mt-2">
          <span className="text-[11px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
            Desktop Shortcuts
          </span>
          <div className="grid grid-cols-3 gap-2 text-xs font-mono">
            <div className="flex items-center justify-between p-1.5 rounded bg-[#0a0a0a] border border-[#262626]">
              <span className="text-[#a1a1a1]">Zoom In</span>
              <kbd className="px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#ededed] border border-[#333333]">Ctrl +</kbd>
            </div>
            <div className="flex items-center justify-between p-1.5 rounded bg-[#0a0a0a] border border-[#262626]">
              <span className="text-[#a1a1a1]">Zoom Out</span>
              <kbd className="px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#ededed] border border-[#333333]">Ctrl -</kbd>
            </div>
            <div className="flex items-center justify-between p-1.5 rounded bg-[#0a0a0a] border border-[#262626]">
              <span className="text-[#a1a1a1]">Reset (100%)</span>
              <kbd className="px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#ededed] border border-[#333333]">Ctrl 0</kbd>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
