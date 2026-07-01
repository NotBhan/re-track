/**
 * IndexRepository — import a repository into Cognee memory.
 */

import { useState } from "react";
import { FolderInput, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { indexRepository, IndexRepositoryResponse } from "../lib/api";

export default function IndexRepository() {
  const [path, setPath] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [batchSize, setBatchSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IndexRepositoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleIndex = async () => {
    if (!path.trim() || !datasetName.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await indexRepository({
        repository_path: path.trim(),
        dataset_name: datasetName.trim(),
        batch_size: batchSize,
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Indexing failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Index Repository
      </h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Import a repository into Cognee persistent memory
      </p>

      {/* Form */}
      <div className="space-y-4 mb-8">
        {/* Repository Path */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Repository Path
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={path}
              onChange={(e) => {
                setPath(e.target.value);
                if (!datasetName) {
                  setDatasetName(e.target.value.split("/").pop() || "repo");
                }
              }}
              placeholder="/path/to/your/repository"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={async () => {
                try {
                  const { open } = await import("@tauri-apps/plugin-dialog");
                  const selected = await open({ directory: true, multiple: false });
                  if (selected) {
                    setPath(selected);
                    if (!datasetName) {
                      setDatasetName(selected.split("/").pop() || "repo");
                    }
                  }
                } catch {
                  // Dialog not available in browser
                }
              }}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              title="Browse for folder"
            >
              <FolderInput size={18} />
            </button>
          </div>
        </div>

        {/* Dataset Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Dataset Name
          </label>
          <input
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="my-project"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Batch Size */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Batch Size: {batchSize}
          </label>
          <input
            type="range"
            min="1"
            max="100"
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Index Button */}
        <button
          onClick={handleIndex}
          disabled={loading || !path.trim() || !datasetName.trim()}
          className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              Indexing...
            </>
          ) : (
            <>
              <FolderInput size={18} />
              Index Repository
            </>
          )}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className={`p-4 rounded-lg border ${result.success ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"}`}>
          <div className="flex items-center gap-2 mb-2">
            {result.success ? (
              <CheckCircle className="text-green-500" size={20} />
            ) : (
              <XCircle className="text-red-500" size={20} />
            )}
            <span className="font-medium text-gray-900 dark:text-white">
              {result.success ? "Indexing Complete" : "Indexing Failed"}
            </span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
            <p>Dataset: {result.dataset_name}</p>
            <p>Files: {result.processed_files}/{result.total_files} processed</p>
            {result.failed_files > 0 && (
              <p className="text-red-600">{result.failed_files} files failed</p>
            )}
            <p>Batches: {result.total_batches}</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center gap-2">
            <XCircle className="text-red-500" size={20} />
            <span className="font-medium text-red-700 dark:text-red-400">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}
