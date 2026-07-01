export function OllamaSettings() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-[24px] leading-[32px] tracking-[-0.01em] font-semibold text-on-surface mb-2">
          Ollama Configuration
        </h2>
        <p className="text-[14px] leading-[20px] text-on-surface-variant">
          Set up your local inference engine and default models.
        </p>
      </div>

      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sm">
        <div className="space-y-6">
          {/* Endpoint */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-outline-variant/50 pb-6">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Local Endpoint
              </label>
            </div>
            <div className="md:w-2/3">
              <input
                type="text"
                defaultValue="http://127.0.0.1:11434"
                className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-mono text-[13px] leading-[20px] transition-colors"
              />
            </div>
          </div>

          {/* Model */}
          <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
            <div className="md:w-1/3">
              <label className="text-[12px] leading-[16px] tracking-[0.02em] font-medium text-on-surface block">
                Default Model
              </label>
              <span className="text-[14px] leading-[20px] text-outline text-xs mt-1 block">
                Used for embeddings and basic inference if not specified in
                request.
              </span>
            </div>
            <div className="md:w-2/3">
              <select className="w-full bg-surface-container h-10 px-3 rounded-md border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary text-on-surface text-[14px] leading-[20px] transition-colors appearance-none">
                <option value="llama3">llama3:8b</option>
                <option value="mistral">mistral:instruct</option>
                <option value="nomic-embed-text">nomic-embed-text</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
