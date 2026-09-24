import React, { useState, useEffect } from "react";
import { RefreshCw, AlertCircle, ShieldAlert } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { toast } from "../../app/providers/ToastProvider";

export const ProviderSettings: React.FC = () => {
  const {
    activeProvider,
    activeEndpoint,
    activeModel,
    configuredModel,
    providerReachable,
    quantizationWarning,
    discoveredModels,
    discovering,
    discoveryError,
    probeProvider,
    saveProvider,
    savingSettings,
    fetchProviderStatus,
    fetchSettings,
    appSettings,
  } = useSystemStore();

  const [provider, setProvider] = useState(activeProvider || "ollama");
  const [endpoint, setEndpoint] = useState(activeEndpoint || "http://localhost:11434/v1");
  const [selectedModel, setSelectedModel] = useState(activeModel || configuredModel || "");
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    fetchProviderStatus();
    fetchSettings();
  }, [fetchProviderStatus, fetchSettings]);

  useEffect(() => {
    if (activeProvider) setProvider(activeProvider);
    if (activeEndpoint) setEndpoint(activeEndpoint);
    if (activeModel || configuredModel) setSelectedModel(activeModel || configuredModel || "");
  }, [activeProvider, activeEndpoint, activeModel, configuredModel]);

  const handleProviderChange = (p: string) => {
    setProvider(p);
    if (p === "lmstudio") {
      setEndpoint("http://localhost:1234/v1");
    } else if (p === "ollama") {
      setEndpoint("http://localhost:11434/v1");
    }
  };

  const handleProbe = async () => {
    await probeProvider(provider, endpoint, apiKey);
    toast.info("Discovery probe sent to endpoint");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedModel.trim()) {
      toast.error("Please select or enter a model name");
      return;
    }

    const ok = await saveProvider(provider, endpoint, selectedModel.trim(), apiKey);
    if (ok) {
      toast.success(`Active inference provider switched to ${provider} (${selectedModel})`);
    } else {
      toast.error("Failed to update provider configuration");
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      {/* Identity State Summary */}
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col gap-3">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Runtime Model Identity
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[11px] text-slate-400 block mb-0.5">Configured Model</span>
            <span className="text-xs font-semibold text-slate-200 font-mono">
              {configuredModel || "phi4-mini"}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[11px] text-slate-400 block mb-0.5">Active/Verified Model</span>
            <span className="text-xs font-semibold text-emerald-400 font-mono">
              {activeModel || (providerReachable ? "active" : "unverified")}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[11px] text-slate-400 block mb-0.5">Embedding Model</span>
            <span className="text-xs font-semibold text-slate-200 font-mono">
              {appSettings?.embedding_model || "nomic-embed-text"}
            </span>
          </div>
        </div>

        {quantizationWarning && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
            <span>{quantizationWarning}</span>
          </div>
        )}
      </div>

      {/* Provider & Model Form */}
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        {/* Provider Radio Pills */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-300">Inference Provider</label>
          <div className="flex p-1 bg-white/[0.03] border border-white/[0.06] rounded-lg max-w-md">
            {[
              { id: "lmstudio", label: "LM Studio" },
              { id: "ollama", label: "Ollama" },
              { id: "openai_compatible", label: "OpenAI Compatible" },
            ].map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleProviderChange(item.id)}
                className={`flex-1 py-1.5 rounded-md text-xs font-medium transition-all ${
                  provider === item.id
                    ? "bg-white/[0.1] text-white shadow-xs"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Base URL & Probe button */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-300">Endpoint Base URL</label>
          <div className="flex gap-2">
            <Input
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder="http://localhost:1234/v1"
            />
            <Button
              type="button"
              variant="secondary"
              loading={discovering}
              onClick={handleProbe}
              title="Probe endpoint to discover loaded models"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Probe
            </Button>
          </div>
        </div>

        {/* API Key if OpenAI compatible */}
        {provider === "openai_compatible" && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-300">API Key</label>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
            />
          </div>
        )}

        {/* Model Selection */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-slate-300">Target Model</label>
            {discoveredModels.length > 0 && (
              <span className="text-[11px] text-slate-400 font-mono">
                {discoveredModels.length} models discovered
              </span>
            )}
          </div>

          {discoveredModels.length > 0 ? (
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-[#11141a] text-xs font-mono text-slate-200 border border-white/[0.08] rounded-lg px-3.5 py-2.5 outline-none cursor-pointer focus:border-sky-500/50"
            >
              {discoveredModels.map((m) => (
                <option key={m.model_id} value={m.name || m.model_id}>
                  {m.name || m.model_id} {m.quantization ? `(${m.quantization})` : ""}
                </option>
              ))}
            </select>
          ) : (
            <Input
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="e.g. qwen2.5:0.5b or phi4-mini"
            />
          )}
        </div>

        {discoveryError && (
          <div className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{discoveryError}</span>
          </div>
        )}

        {/* Submit action */}
        <div className="pt-2">
          <Button type="submit" loading={savingSettings} size="md">
            Save & Switch Provider
          </Button>
        </div>
      </form>
    </div>
  );
};
