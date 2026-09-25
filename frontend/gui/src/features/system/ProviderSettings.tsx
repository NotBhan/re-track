import React, { useState, useEffect } from "react";
import { RefreshCw, AlertCircle, ShieldAlert } from "lucide-react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { Select } from "../../components/Select";
import { toast } from "../../app/providers/ToastProvider";
import { cn } from "../../lib/utils";

const PROVIDER_OPTIONS = [
  { id: "lmstudio", label: "LM Studio" },
  { id: "ollama", label: "Ollama" },
  { id: "openai_compatible", label: "OpenAI Compatible" },
];

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
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3">
        <h4 className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
          Runtime Model Identity
        </h4>

        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-3">
          <div className="flex flex-col gap-0.5">
            <dt className="text-[11px] text-[#707070]">Configured model</dt>
            <dd className="text-xs font-mono text-[#ededed] truncate">
              {configuredModel || "not configured"}
            </dd>
          </div>

          <div className="flex flex-col gap-0.5">
            <dt className="text-[11px] text-[#707070]">Active / verified model</dt>
            <dd
              className={cn(
                "text-xs font-mono truncate",
                providerReachable ? "text-[#10b981]" : "text-[#707070]"
              )}
            >
              {activeModel || (providerReachable ? "active" : "unverified")}
            </dd>
          </div>

          <div className="flex flex-col gap-0.5">
            <dt className="text-[11px] text-[#707070]">Embedding model</dt>
            <dd className="text-xs font-mono text-[#ededed] truncate">
              {appSettings?.embedding_model || "not configured"}
            </dd>
          </div>
        </dl>

        {quantizationWarning && (
          <div className="flex items-center gap-2 p-2.5 rounded-sm bg-[#1c1304] border border-[#f59e0b]/25 text-[#f59e0b] text-xs">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{quantizationWarning}</span>
          </div>
        )}
      </div>

      {/* Provider & Model Form */}
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        {/* Provider Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#a1a1a1]">Inference provider</label>
          <div className="flex p-1 bg-[#121212] border border-[#262626] rounded-sm max-w-md">
            {PROVIDER_OPTIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleProviderChange(item.id)}
                className={cn(
                  "flex-1 py-1.5 rounded-[4px] text-xs font-medium transition-colors border",
                  provider === item.id
                    ? "bg-[#1f1f1f] text-[#ededed] border-[#333333]"
                    : "text-[#707070] hover:text-[#ededed] border-transparent"
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Base URL & Probe button */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[#a1a1a1]">Endpoint base URL</label>
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
            <label className="text-xs font-medium text-[#a1a1a1]">API key</label>
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
            <label className="text-xs font-medium text-[#a1a1a1]">Target model</label>
            {discoveredModels.length > 0 && (
              <span className="text-[11px] text-[#707070] font-mono">
                {discoveredModels.length} models discovered
              </span>
            )}
          </div>

          {discoveredModels.length > 0 ? (
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              options={discoveredModels.map((m) => ({
                value: m.name || m.model_id,
                label: m.name || m.model_id,
                hint: m.quantization || undefined,
              }))}
              placeholder="Select a discovered model"
              ariaLabel="Target model"
              className="w-full max-w-md"
            />
          ) : (
            <Input
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="e.g. qwen2.5:0.5b or phi4-mini"
            />
          )}
        </div>

        {discoveryError && (
          <div className="flex items-center gap-2 p-3 bg-[#180808] border border-[#451a1a] text-[#f87171] rounded-sm text-xs">
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
