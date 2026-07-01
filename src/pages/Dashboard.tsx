/**
 * Dashboard — landing page with status overview and quick actions.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderInput, MessageSquare, Activity, Database, Cpu } from "lucide-react";
import { health, getBackendStatus, HealthResponse, BackendStatusResponse } from "../lib/api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [statusData, setStatusData] = useState<BackendStatusResponse | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [h, s] = await Promise.all([health(), getBackendStatus()]);
        setHealthData(h);
        setStatusData(s);
      } catch {
        // Backend not running
      }
    };
    load();
  }, []);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          AndesContext
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Local-first AI memory for software development
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <button
          onClick={() => navigate("/index")}
          className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors text-left"
        >
          <FolderInput className="text-blue-500" size={24} />
          <div>
            <div className="font-semibold text-gray-900 dark:text-white">Index Repository</div>
            <div className="text-sm text-gray-500">Import a project into memory</div>
          </div>
        </button>

        <button
          onClick={() => navigate("/context")}
          className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 transition-colors text-left"
        >
          <MessageSquare className="text-green-500" size={24} />
          <div>
            <div className="font-semibold text-gray-900 dark:text-white">New Context</div>
            <div className="text-sm text-gray-500">Generate a Context Package</div>
          </div>
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatusCard
          icon={<Cpu size={20} />}
          title="Ollama"
          value={healthData?.ollama_reachable ? "Connected" : "Disconnected"}
          color={healthData?.ollama_reachable ? "green" : "red"}
          subtitle={statusData?.llm_model || "Unknown model"}
        />
        <StatusCard
          icon={<Database size={20} />}
          title="Cognee"
          value={healthData?.cognee_initialized ? "Initialized" : "Not Ready"}
          color={healthData?.cognee_initialized ? "green" : "yellow"}
          subtitle={statusData ? `${statusData.vector_db} + ${statusData.graph_db}` : ""}
        />
        <StatusCard
          icon={<Activity size={20} />}
          title="Status"
          value={healthData?.status === "ok" ? "Healthy" : "Checking..."}
          color={healthData?.status === "ok" ? "green" : "yellow"}
          subtitle={healthData ? `v${healthData.version}` : ""}
        />
      </div>
    </div>
  );
}

function StatusCard({
  icon,
  title,
  value,
  color,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  color: "green" | "yellow" | "red";
  subtitle: string;
}) {
  const colorMap = {
    green: "text-green-500",
    yellow: "text-yellow-500",
    red: "text-red-500",
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        <span className={colorMap[color]}>{icon}</span>
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</span>
      </div>
      <div className="text-lg font-semibold text-gray-900 dark:text-white">{value}</div>
      {subtitle && (
        <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">{subtitle}</div>
      )}
    </div>
  );
}
