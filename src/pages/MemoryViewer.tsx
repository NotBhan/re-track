/**
 * MemoryViewer — browse and manage Cognee memory.
 */

import { useState } from "react";
import { Database, Trash2, AlertTriangle } from "lucide-react";
import { forgetDataset } from "../lib/api";

export default function MemoryViewer() {
  const [dataset, setDataset] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleForget = async () => {
    if (!dataset.trim()) return;

    try {
      const response = await forgetDataset({ dataset: dataset.trim() });
      setResult(response);
      setShowConfirm(false);
      if (response.success) {
        setDataset("");
      }
    } catch (e) {
      setResult({
        success: false,
        message: e instanceof Error ? e.message : "Failed to forget dataset",
      });
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Memory Viewer
      </h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Manage datasets stored in Cognee memory
      </p>

      {/* Forget Dataset */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Trash2 size={18} />
          Forget Dataset
        </h2>

        <div className="flex gap-2">
          <input
            type="text"
            value={dataset}
            onChange={(e) => setDataset(e.target.value)}
            placeholder="Dataset name to delete"
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          />
          <button
            onClick={() => dataset.trim() && setShowConfirm(true)}
            disabled={!dataset.trim()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Forget
          </button>
        </div>

        {/* Confirmation Dialog */}
        {showConfirm && (
          <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="text-yellow-500" size={18} />
              <span className="font-medium text-yellow-800 dark:text-yellow-200">
                Are you sure?
              </span>
            </div>
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
              This will permanently delete all memory for dataset "{dataset}".
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleForget}
                className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
              >
                Yes, forget it
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 bg-gray-200 dark:bg-gray-700 text-sm rounded hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className={`mt-4 p-3 rounded-lg text-sm ${result.success ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300" : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"}`}>
            {result.message}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="flex items-start gap-2">
          <Database className="text-blue-500 mt-0.5" size={16} />
          <div className="text-sm text-blue-700 dark:text-blue-300">
            <p className="font-medium">Memory Management</p>
            <p className="mt-1">
              Datasets are created when you index repositories. Each dataset contains
              the indexed memories for that repository. Forgetting a dataset permanently
              removes all its memories from Cognee.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
