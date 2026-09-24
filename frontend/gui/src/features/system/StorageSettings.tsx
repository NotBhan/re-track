import React, { useState, useEffect } from "react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { toast } from "../../app/providers/ToastProvider";

export const StorageSettings: React.FC = () => {
  const { appSettings, fetchSettings, saveStorageSettings, savingSettings } = useSystemStore();

  const [vectorDb, setVectorDb] = useState(appSettings?.vector_db || "lancedb");
  const [graphDb, setGraphDb] = useState(appSettings?.graph_db || "kuzu");
  const [enableKg, setEnableKg] = useState(appSettings?.enable_kg_extraction ?? true);
  const [autoLink, setAutoLink] = useState(appSettings?.auto_link_entities ?? false);
  const [caching, setCaching] = useState(appSettings?.caching ?? false);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  useEffect(() => {
    if (appSettings) {
      setVectorDb(appSettings.vector_db);
      setGraphDb(appSettings.graph_db);
      setEnableKg(appSettings.enable_kg_extraction);
      setAutoLink(appSettings.auto_link_entities);
      setCaching(appSettings.caching);
    }
  }, [appSettings]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const ok = await saveStorageSettings({
      vector_db: vectorDb,
      graph_db: graphDb,
      enable_kg_extraction: enableKg,
      auto_link_entities: autoLink,
      caching,
    });
    if (ok) {
      toast.success("Storage and pipeline settings persisted");
    } else {
      toast.error("Failed to save storage settings");
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      {/* Canonical Storage Paths */}
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col gap-3">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Storage Directories
        </h4>

        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] text-slate-400">Data Root</span>
            <div className="text-xs font-mono text-slate-200 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] truncate">
              {appSettings?.data_root || "~/.retrack/data"}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[11px] text-slate-400">System Root</span>
            <div className="text-xs font-mono text-slate-200 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] truncate">
              {appSettings?.system_root || "~/.retrack/system"}
            </div>
          </div>
        </div>
      </div>

      {/* Database Engines & Pipeline Options */}
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-300">Vector Storage Engine</label>
            <select
              value={vectorDb}
              onChange={(e) => setVectorDb(e.target.value)}
              className="bg-[#11141a] text-xs font-mono text-slate-200 border border-white/[0.08] rounded-lg px-3.5 py-2 outline-none"
            >
              <option value="lancedb">LanceDB (Deterministic Flat/IVF)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-300">Graph Storage Engine</label>
            <select
              value={graphDb}
              onChange={(e) => setGraphDb(e.target.value)}
              className="bg-[#11141a] text-xs font-mono text-slate-200 border border-white/[0.08] rounded-lg px-3.5 py-2 outline-none"
            >
              <option value="kuzu">Kùzu Graph Engine</option>
            </select>
          </div>
        </div>

        {/* Checkbox Toggles */}
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col gap-3">
          <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={enableKg}
              onChange={(e) => setEnableKg(e.target.checked)}
              className="rounded bg-white/[0.06] border-white/[0.1] text-sky-500 focus:ring-0"
            />
            <span>Enable Knowledge Graph Entity Extraction</span>
          </label>

          <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoLink}
              onChange={(e) => setAutoLink(e.target.checked)}
              className="rounded bg-white/[0.06] border-white/[0.1] text-sky-500 focus:ring-0"
            />
            <span>Auto-link related semantic entities</span>
          </label>

          <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={caching}
              onChange={(e) => setCaching(e.target.checked)}
              className="rounded bg-white/[0.06] border-white/[0.1] text-sky-500 focus:ring-0"
            />
            <span>Enable Intermediate Ingestion Caching</span>
          </label>
        </div>

        <div className="pt-2">
          <Button type="submit" loading={savingSettings} size="md">
            Save Storage Configuration
          </Button>
        </div>
      </form>
    </div>
  );
};
