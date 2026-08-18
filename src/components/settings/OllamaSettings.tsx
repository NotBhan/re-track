import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useHealthStore } from "@/stores/health-store";
import { updateProvider } from "@/lib/api";
import type { UpdateProviderRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";

const PROVIDER_DEFAULTS: Record<
  UpdateProviderRequest["provider"],
  { label: string; url: string; apiKey: string }
> = {
  ollama: {
    label: "Ollama",
    url: "http://127.0.0.1:11434/v1",
    apiKey: "ollama",
  },
  lmstudio: {
    label: "LM Studio",
    url: "http://127.0.0.1:1234/v1",
    apiKey: "lm-studio",
  },
  openai_compatible: {
    label: "Custom OpenAI Compatible",
    url: "http://127.0.0.1:8080/v1",
    apiKey: "local",
  },
};

export function OllamaSettings() {
  const { status, ollamaRunning, pollHealth } = useHealthStore();

  // Derive current provider from active status.
  // Heuristic: LM Studio default port is 1234, Ollama is 11434.
  const detectedProvider = (): UpdateProviderRequest["provider"] => {
    if (!status) return "lmstudio";
    const port = status.ollama_port;
    if (port === 11434) return "ollama";
    if (port === 1234) return "lmstudio";
    return "openai_compatible";
  };

  const [provider, setProvider] =
    useState<UpdateProviderRequest["provider"]>(detectedProvider);
  const [baseUrl, setBaseUrl] = useState(
    status
      ? `http://${status.ollama_host}:${status.ollama_port}/v1`
      : PROVIDER_DEFAULTS["lmstudio"].url
  );
  const [model, setModel] = useState(
    status?.llm_model ?? "phi4-mini:q6_k"
  );
  const [apiKey, setApiKey] = useState(
    PROVIDER_DEFAULTS[detectedProvider()].apiKey
  );
  const [loadedModels, setLoadedModels] = useState<string[]>([]);

  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<
    { ok: boolean; message: string } | null
  >(null);

  // When provider dropdown changes, pre-fill URL and apiKey defaults.
  const handleProviderChange = (p: UpdateProviderRequest["provider"]) => {
    setProvider(p);
    setBaseUrl(PROVIDER_DEFAULTS[p].url);
    setApiKey(PROVIDER_DEFAULTS[p].apiKey);
    setLoadedModels([]);
    setSaveResult(null);
  };

  const handleApply = async () => {
    setSaving(true);
    setSaveResult(null);
    try {
      const result = await updateProvider({ provider, base_url: baseUrl, model, api_key: apiKey });
      setLoadedModels(result.loaded_models ?? []);
      // Auto-select first loaded model if current model isn't loaded
      if (result.loaded_models?.length > 0 && !result.loaded_models.includes(model)) {
        setModel(result.loaded_models[0]);
      }
      setSaveResult({
        ok: result.reachable,
        message: result.reachable
          ? `Connected · ${result.loaded_models.length} model(s) loaded`
          : "Provider unreachable — check URL and that the server is running",
      });
      // Refresh sidebar health status
      await pollHealth();
    } catch (err) {
      setSaveResult({ ok: false, message: String(err) });
    } finally {
      setSaving(false);
    }
  };

  // Refresh loaded model list on mount if backend is already up
  useEffect(() => {
    if (status && ollamaRunning) {
      updateProvider({
        provider: detectedProvider(),
        base_url: `http://${status.ollama_host}:${status.ollama_port}/v1`,
        model: status.llm_model,
        api_key: apiKey,
      }).then((r) => {
        if (r.loaded_models?.length) setLoadedModels(r.loaded_models);
      }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const inputCls =
    "w-full bg-[#050505] h-8 px-3 rounded-md border border-[#222222] focus:border-white focus:outline-none text-neutral-200 font-mono text-xs transition-colors placeholder:text-neutral-600";
  const rowCls =
    "flex flex-col md:flex-row md:items-start gap-2 md:gap-8 border-b border-[#181818] pb-4";
  const labelCls = "text-xs font-medium text-neutral-200 block";
  const subCls = "text-xs text-neutral-500 mt-0.5 block";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white tracking-tight mb-0.5">
          Inference &amp; Provider
        </h2>
        <p className="text-xs text-neutral-500">
          Configure your local inference engine. Changes apply immediately — no restart needed.
        </p>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg p-4 space-y-4">
        {/* Provider dropdown */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Inference Backend</label>
            <span className={subCls}>Select your local runner.</span>
          </div>
          <div className="md:w-2/3">
            <select
              value={provider}
              onChange={(e) =>
                handleProviderChange(e.target.value as UpdateProviderRequest["provider"])
              }
              className={inputCls}
            >
              {(Object.keys(PROVIDER_DEFAULTS) as Array<UpdateProviderRequest["provider"]>).map(
                (p) => (
                  <option key={p} value={p}>
                    {PROVIDER_DEFAULTS[p].label}
                  </option>
                )
              )}
            </select>
          </div>
        </div>

        {/* Base URL */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Base URL</label>
            <span className={subCls}>Include /v1 suffix for OpenAI-compatible APIs.</span>
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

        {/* Active Model */}
        <div className={rowCls}>
          <div className="md:w-1/3">
            <label className={labelCls}>Active Model</label>
            <span className={subCls}>
              Tuned for phi4:mini (Q6_K+ recommended).
            </span>
          </div>
          <div className="md:w-2/3 space-y-1.5">
            {/* If we have a list of loaded models, show a select + text fallback */}
            {loadedModels.length > 0 ? (
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className={inputCls}
              >
                {loadedModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. phi4-mini:q6_k"
                className={inputCls}
              />
            )}
            {loadedModels.length > 0 && (
              <p className="text-[10px] text-neutral-500 font-mono">
                {loadedModels.length} model(s) loaded in {PROVIDER_DEFAULTS[provider].label}
              </p>
            )}
          </div>
        </div>

        {/* API Key */}
        <div className="flex flex-col md:flex-row md:items-start gap-2 md:gap-8">
          <div className="md:w-1/3">
            <label className={labelCls}>API Key</label>
            <span className={subCls}>
              Use &ldquo;ollama&rdquo; or &ldquo;lm-studio&rdquo; for local servers.
            </span>
          </div>
          <div className="md:w-2/3">
            <input
              type="text"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>
      </div>

      {/* Footer: status + apply */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-h-[24px]">
          {saving && (
            <>
              <Loader2 className="w-3.5 h-3.5 text-neutral-400 animate-spin" />
              <span className="text-xs font-mono text-neutral-400">Connecting…</span>
            </>
          )}
          {!saving && saveResult && (
            <>
              {saveResult.ok ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              )}
              <span
                className={`text-xs font-mono ${
                  saveResult.ok ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {saveResult.message}
              </span>
            </>
          )}
        </div>

        <Button
          onClick={handleApply}
          disabled={saving}
          size="sm"
          className="w-[125px] justify-center gap-1.5 h-7.5 px-3 text-xs bg-white text-black font-medium hover:bg-neutral-200 rounded-md cursor-pointer shadow-xs disabled:opacity-60"
        >
          {saving ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
          <span>{saving ? "Applying..." : "Apply & Test"}</span>
        </Button>
      </div>
    </div>
  );
}
