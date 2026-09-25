import React, { useState, useEffect } from "react";
import { useSystemStore } from "../../stores/systemStore";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
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
      <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3">
        <h4 className="text-[10px] font-semibold text-[#707070] uppercase tracking-wider font-mono">
          Storage Directories
        </h4>

        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="text-[11px] text-[#707070]">Data root</span>
            <div className="text-xs font-mono text-[#ededed] p-2 rounded-sm bg-[#121212] border border-[#262626] truncate">
              {appSettings?.data_root || "Unavailable"}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-[11px] text-[#707070]">System root</span>
            <div className="text-xs font-mono text-[#ededed] p-2 rounded-sm bg-[#121212] border border-[#262626] truncate">
              {appSettings?.system_root || "Unavailable"}
            </div>
          </div>
        </div>
      </div>

      {/* Database Engines & Pipeline Options */}
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#a1a1a1]">Vector storage engine</label>
            <Select
              value={vectorDb}
              onChange={setVectorDb}
              options={[{ value: "lancedb", label: "LanceDB (deterministic)" }]}
              disabled
              ariaLabel="Vector storage engine"
              title="The backend supports a single vector engine"
              className="w-full"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#a1a1a1]">Graph storage engine</label>
            <Select
              value={graphDb}
              onChange={setGraphDb}
              options={[{ value: "kuzu", label: "Kùzu graph engine" }]}
              disabled
              ariaLabel="Graph storage engine"
              title="The backend supports a single graph engine"
              className="w-full"
            />
          </div>
        </div>

        {/* Checkbox Toggles */}
        <div className="p-4 rounded-lg bg-[#0a0a0a] border border-[#262626] flex flex-col gap-3">
          <label className="flex items-center gap-2.5 text-xs text-[#a1a1a1] cursor-pointer select-none hover:text-[#ededed] transition-colors">
            <input
              type="checkbox"
              checked={enableKg}
              onChange={(e) => setEnableKg(e.target.checked)}
              className="accent-[#ededed]"
            />
            <span>Enable knowledge graph entity extraction</span>
          </label>

          <label className="flex items-center gap-2.5 text-xs text-[#a1a1a1] cursor-pointer select-none hover:text-[#ededed] transition-colors">
            <input
              type="checkbox"
              checked={autoLink}
              onChange={(e) => setAutoLink(e.target.checked)}
              className="accent-[#ededed]"
            />
            <span>Auto-link related semantic entities</span>
          </label>

          <label className="flex items-center gap-2.5 text-xs text-[#a1a1a1] cursor-pointer select-none hover:text-[#ededed] transition-colors">
            <input
              type="checkbox"
              checked={caching}
              onChange={(e) => setCaching(e.target.checked)}
              className="accent-[#ededed]"
            />
            <span>Enable intermediate ingestion caching</span>
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
