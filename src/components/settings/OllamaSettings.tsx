import { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Search,
  Eye,
  EyeOff,
  AlertTriangle,
} from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { useSettingsStore } from "@/stores/settings-store";
import { Button } from "@/components/ui/button";

const PROVIDER_DEFAULTS: Record<
  string,
  { label: string; url: string; defaultKeyPlaceholder: string }
> = {
  ollama: {
    label: "Ollama",
    url: "http://127.0.0.1:11434/v1",
    defaultKeyPlaceholder: "ollama (or local)",
  },
  lmstudio: {
    label: "LM Studio",
    url: "http://127.0.0.1:1234/v1",
    defaultKeyPlaceholder: "lm-studio (or local)",
  },
  openai_compatible: {
    label: "Custom OpenAI-Compatible",
    url: "http://127.0.0.1:8080/v1",
    defaultKeyPlaceholder: "API Key (optional)",
  },
};

export function OllamaSettings() {
  const { pollHealth } = useHealthStore();
  const {
    provider,
    endpoint,
    model,
    apiKeyConfigured,
    apiKeyMasked,
    providerReachable,
    providerHealthState,
    quantizationWarning,
    availableModels,
    discovering,
    discoveryStatus,
    discoveryMessage,
    discoveryError,
    saving,
    saveSuccess,
    statusMessage,
    fetchSettings,
    discoverModels,
    saveProviderSettings,
    clearStatus,
  } = useSettingsStore();


  // Local transient form state
  const [selectedProvider, setSelectedProvider] = useState(provider || "ollama");
  const [baseUrl, setBaseUrl] = useState(endpoint || "http://127.0.0.1:11434/v1");
  const [selectedModel, setSelectedModel] = useState(model || "phi4-mini");
  const [newApiKey, setNewApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);

  // Authoritative hydration on mount
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Sync transient form when store updates from backend
  useEffect(() => {
    if (provider) setSelectedProvider(provider);
    if (endpoint) setBaseUrl(endpoint);
    if (model) setSelectedModel(model);
  }, [provider, endpoint, model]);

  const handleProviderChange = (newP: string) => {
    setSelectedProvider(newP);
    const def = PROVIDER_DEFAULTS[newP] || PROVIDER_DEFAULTS.ollama;
    setBaseUrl(def.url);
    clearStatus();
  };

  const handleDiscover = async () => {
    clearStatus();
    const res = await discoverModels(selectedProvider, baseUrl, newApiKey || undefined);
    if (res && res.models && res.models.length > 0) {
      // If current selectedModel is not in discovered models, default to first discovered
      const hasMatch = res.models.some(
        (m) => m.model_id === selectedModel || m.name === selectedModel
      );
      if (!hasMatch) {
        setSelectedModel(res.models[0].model_id);
      }
    }
  };

  const handleApply = async () => {
    const success = await saveProviderSettings(
      selectedProvider,
      baseUrl,
      selectedModel,
      newApiKey || undefined
    );
    if (success) {
      setNewApiKey("");
      await pollHealth();
    }
  };

  const inputCls =
    "w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] focus:border-white focus:outline-none text-neutral-200 font-mono text-xs transition-colors placeholder:text-neutral-600";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#181818] pb-4";
  const labelCls = "text-xs font-medium text-neutral-200 block";
  const subCls = "text-xs text-neutral-500 mt-0.5 block";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
            Inference &amp; Provider Configuration
          </h2>
          <p className="text-xs text-neutral-500">
            Configure authoritative local or remote LLM inference endpoints. Configuration survives restarts.
          </p>
        </div>

        {/* Health state badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#111111] border border-[#222222]">
          <span
            className={`w-2 h-2 rounded-full ${
              providerHealthState === "healthy"
                ? "bg-emerald-400"
                : providerHealthState === "degraded"
                ? "bg-amber-400"
                : "bg-red-400"
            }`}
          />
          <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-300">
            {providerHealthState || (providerReachable ? "healthy" : "unavailable")}
          </span>
        </div>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
        {/* Provider dropdown */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Inference Provider</label>
            <span className={subCls}>Authoritative backend runner selection.</span>
          </div>
          <div className="md:w-2/3">
            <select
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className={inputCls}
            >
              {Object.keys(PROVIDER_DEFAULTS).map((p) => (
                <option key={p} value={p}>
                  {PROVIDER_DEFAULTS[p].label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Base URL */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Base URL</label>
            <span className={subCls}>Endpoint URL (normalized with /v1 where required).</span>
          </div>
          <div className="md:w-2/3">
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>

        {/* API Key */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>API Key</label>
            <span className={subCls}>
              {apiKeyConfigured
                ? `Key configured (${apiKeyMasked}). Enter a new key to change.`
                : "Required for authenticated local or remote endpoints."}
            </span>
          </div>
          <div className="md:w-2/3 relative">
            <input
              type={showKey ? "text" : "password"}
              value={newApiKey}
              onChange={(e) => setNewApiKey(e.target.value)}
              placeholder={
                apiKeyConfigured
                  ? `Configured (${apiKeyMasked}) — leave blank to keep`
                  : PROVIDER_DEFAULTS[selectedProvider]?.defaultKeyPlaceholder || "Optional API Key"
              }
              className={`${inputCls} pr-9`}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2.5 top-2 text-neutral-400 hover:text-white transition-colors"
            >
              {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Model Discovery Section */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Active Model</label>
            <span className={subCls}>
              phi4:mini (Q6_K+) is tuned for optimal reasoning in RE:Track.
            </span>
          </div>
          <div className="md:w-2/3 space-y-2">
            <div className="flex gap-2">
              {availableModels.length > 0 ? (
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className={inputCls}
                >
                  {availableModels.map((m) => (
                    <option key={m.model_id} value={m.model_id}>
                      {m.name} ({m.quantization || "unknown"}) {m.is_phi4_mini ? "★ phi4" : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  placeholder="e.g. phi4-mini:q6_k"
                  className={inputCls}
                />
              )}

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleDiscover}
                disabled={discovering}
                className="h-8 px-3 text-xs bg-[#141414] hover:bg-[#222222] text-neutral-200 border-[#2a2a2a] shrink-0"
              >
                {discovering ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-1.5" />
                ) : (
                  <Search className="w-3 h-3 mr-1.5" />
                )}
                <span>Discover</span>
              </Button>
            </div>

            {/* Discovery Status Feedback */}
            {discoveryStatus === "available" && availableModels.length > 0 && (
              <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-mono">
                <CheckCircle2 className="w-3 h-3" />
                <span>{discoveryMessage || `Discovered ${availableModels.length} model(s)`}</span>
              </div>
            )}

            {discoveryStatus === "reachable_but_empty" && (
              <div className="p-2.5 rounded-md bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-medium">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>No models loaded</span>
                </div>
                <p className="text-[11px] text-amber-200/80">
                  Endpoint is reachable, but 0 models are currently loaded in {selectedProvider}. Load a model in your runner first.
                </p>
              </div>
            )}

            {discoveryStatus === "unreachable" && (
              <div className="p-2.5 rounded-md bg-red-950/30 border border-red-800/40 text-red-300 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-medium">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>Endpoint unreachable</span>
                </div>
                <p className="text-[11px] text-red-200/80">
                  {discoveryMessage || "Could not connect to provider endpoint. Verify that the runner is running."}
                </p>
              </div>
            )}

            {discoveryStatus === "discovery_failed" && (
              <div className="p-2.5 rounded-md bg-red-950/30 border border-red-800/40 text-red-300 text-xs space-y-1">
                <div className="flex items-center gap-1.5 font-medium">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>Discovery failed</span>
                </div>
                <p className="text-[11px] text-red-200/80">
                  {discoveryError || discoveryMessage}
                </p>
              </div>
            )}

            {/* Quantization warning banner */}
            {quantizationWarning && (
              <div className="p-2.5 rounded-md bg-amber-950/20 border border-amber-800/30 text-amber-300/90 text-xs flex items-start gap-2">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
                <span>{quantizationWarning}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer: status + save/apply */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-h-[24px]">
          {saving && (
            <>
              <Loader2 className="w-3.5 h-3.5 text-neutral-400 animate-spin" />
              <span className="text-xs font-mono text-neutral-400">Saving &amp; applying configuration…</span>
            </>
          )}
          {!saving && statusMessage && (
            <>
              {saveSuccess ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              )}
              <span
                className={`text-xs font-mono ${
                  saveSuccess ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {statusMessage}
              </span>
            </>
          )}
        </div>

        <Button
          onClick={handleApply}
          disabled={saving}
          size="sm"
          className="w-[140px] justify-center gap-1.5 h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 rounded-md cursor-pointer shadow-xs disabled:opacity-60"
        >
          {saving ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
          <span>{saving ? "Applying..." : "Save & Apply"}</span>
        </Button>
      </div>
    </div>
  );
}
