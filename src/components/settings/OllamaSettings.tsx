import { useHealthStore } from "@/stores/health-store";

export function OllamaSettings() {
  const status = useHealthStore((s) => s.status);
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
          Inference & Provider Settings
        </h2>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Configure your local/remote inference engines (Ollama, LM Studio, OpenAI-compatible).
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sm">
        <div className="space-y-6">
          {/* Provider Selection */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Inference Backend
              </label>
              <span className="text-[12px] leading-[16px] text-on-surface-variant/70 mt-1 block">
                Select your local runner or OpenAI-compatible server.
              </span>
            </div>
            <div className="md:w-2/3">
              <select
                defaultValue="ollama"
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface text-[14px] leading-[20px] transition-colors"
              >
                <option value="ollama">Ollama (Default: http://127.0.0.1:11434)</option>
                <option value="lmstudio">LM Studio (http://127.0.0.1:1234/v1)</option>
                <option value="openai_compatible">Custom OpenAI Compatible</option>
              </select>
            </div>
          </div>

          {/* Endpoint */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Base URL / Endpoint
              </label>
            </div>
            <div className="md:w-2/3">
              <input
                type="text"
                defaultValue={
                  status
                    ? `http://${status.ollama_host}:${status.ollama_port}`
                    : "http://127.0.0.1:11434"
                }
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors"
              />
            </div>
          </div>

          {/* Model */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Active Reasoning Model
              </label>
              <span className="text-[12px] leading-[16px] text-outline text-xs mt-1 block">
                Tuned for phi4:mini (Q6_K+ recommended for 8GB VRAM/RAM).
              </span>
            </div>
            <div className="md:w-2/3 space-y-2">
              <input
                type="text"
                defaultValue={status?.llm_model ?? "phi4-mini:q6_k"}
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors"
              />
              <p className="text-[11px] text-on-surface-variant/80">
                RE:Track strictly runs loaded models without unapproved automatic downloads.
              </p>
            </div>
          </div>

          {/* Embedding Model */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Embedding Model
              </label>
              <span className="text-[14px] leading-[20px] text-outline text-xs mt-1 block">
                Used for generating vector embeddings.
              </span>
            </div>
            <div className="md:w-2/3">
              <input
                type="text"
                readOnly
                defaultValue={status?.embedding_model ?? "nomic-embed-text"}
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant text-on-surface font-mono text-[13px] leading-[20px] cursor-not-allowed"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
