/**
 * Settings — display backend configuration.
 */

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, Cpu, Database, HardDrive } from "lucide-react";
import { getBackendStatus, BackendStatusResponse } from "../lib/api";

export default function Settings() {
  const [status, setStatus] = useState<BackendStatusResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const s = await getBackendStatus();
        setStatus(s);
      } catch {
        // Backend not running
      }
    };
    load();
  }, []);

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Settings
      </h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Backend configuration and status
      </p>

      {status ? (
        <div className="space-y-6">
          {/* Ollama */}
          <ConfigSection
            icon={<Cpu size={18} />}
            title="Ollama"
            items={[
              { label: "Host", value: status.ollama_host },
              { label: "Port", value: status.ollama_port.toString() },
              { label: "LLM Model", value: status.llm_model },
              { label: "Embedding Model", value: status.embedding_model },
              { label: "Reachable", value: status.ollama_reachable ? "Yes" : "No" },
            ]}
          />

          {/* Storage */}
          <ConfigSection
            icon={<Database size={18} />}
            title="Storage"
            items={[
              { label: "Vector DB", value: status.vector_db },
              { label: "Graph DB", value: status.graph_db },
              { label: "Relational DB", value: status.relational_db },
            ]}
          />

          {/* Paths */}
          <ConfigSection
            icon={<HardDrive size={18} />}
            title="Paths"
            items={[
              { label: "Data Root", value: status.data_root },
              { label: "System Root", value: status.system_root },
            ]}
          />

          {/* About */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
              <SettingsIcon size={16} />
              <span className="text-sm">AndesContext v0.1.0</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Local-first AI memory for software development
            </p>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400">
          <SettingsIcon size={48} className="mx-auto mb-4 opacity-50" />
          <p>Unable to load backend status</p>
          <p className="text-sm mt-1">Make sure the backend is running</p>
        </div>
      )}
    </div>
  );
}

function ConfigSection({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: { label: string; value: string }[];
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">{item.label}</span>
            <span className="text-gray-900 dark:text-gray-200 font-mono text-xs">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
