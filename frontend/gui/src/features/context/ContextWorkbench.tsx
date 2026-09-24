import React, { useState, useEffect } from "react";
import { Compass, Bookmark, Layers, AlertCircle, ArrowRight } from "lucide-react";
import { useContextMenuStore } from "../../stores/contextStore";
import { useRepositoryStore } from "../../stores/repositoryStore";
import { EvidenceViewer } from "./EvidenceViewer";
import { SynthesisOutput } from "./SynthesisOutput";
import { PackageDrawer } from "./PackageDrawer";
import { Button } from "../../components/Button";
import { Input } from "../../components/Input";
import { Dialog } from "../../components/Dialog";
import { EmptyState } from "../../components/EmptyState";
import { toast } from "../../app/providers/ToastProvider";

export const ContextWorkbench: React.FC = () => {
  const {
    taskPrompt,
    setTaskPrompt,
    maxTokens,
    setMaxTokens,
    includeStructuralGraph,
    setIncludeStructuralGraph,
    synthesizing,
    error,
    result,
    synthesize,
    suggestedPrompts,
    fetchPrompts,
    saveCurrentAsPackage,
  } = useContextMenuStore();

  const { selectedRepo } = useRepositoryStore();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [packageName, setPackageName] = useState("");
  const [savingPackage, setSavingPackage] = useState(false);

  useEffect(() => {
    if (selectedRepo?.id) {
      fetchPrompts(selectedRepo.id);
    }
  }, [selectedRepo?.id, fetchPrompts]);

  const handleSynthesize = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim() || synthesizing) return;
    synthesize();
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!packageName.trim()) return;
    setSavingPackage(true);
    try {
      const saved = await saveCurrentAsPackage(packageName.trim());
      if (saved) {
        toast.success(`Context package "${packageName}" saved`);
        setSaveModalOpen(false);
        setPackageName("");
      }
    } catch {
      toast.error("Failed to save package");
    } finally {
      setSavingPackage(false);
    }
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col p-6 gap-5 bg-[#000000]">
      {/* Top Bar: Prompt input area + Suggestions */}
      <div className="flex flex-col gap-3 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-[#ededed] flex items-center gap-2">
              <Compass className="w-4 h-4 text-[#ededed]" />
              <span>Context Studio</span>
            </h2>
            <p className="text-xs text-[#a1a1a1] mt-0.5">
              Synthesize precision coding context backed by deterministic AST evidence and semantic memory.
            </p>
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setDrawerOpen(true)}
            title="Browse saved packages"
          >
            <Bookmark className="w-3.5 h-3.5 mr-1 text-[#a1a1a1]" />
            <span>Saved Packages</span>
          </Button>
        </div>

        {/* Task Input Box */}
        <form onSubmit={handleSynthesize} className="flex flex-col gap-2.5">
          <div className="relative rounded-lg border border-[#262626] bg-[#0a0a0a] p-3 focus-within:border-[#666666] focus-within:ring-1 focus-within:ring-[#ededed]/15 transition-colors">
            <textarea
              rows={2}
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              placeholder="Describe your coding task (e.g. 'Add SQLite authentication middleware with bcrypt sessions')..."
              className="w-full bg-transparent text-sm text-[#ededed] placeholder:text-[#707070] outline-none resize-none leading-relaxed font-sans"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  handleSynthesize(e);
                }
              }}
            />

            <div className="flex items-center justify-between pt-2.5 border-t border-[#1f1f1f]">
              {/* Token & Options Controls */}
              <div className="flex items-center gap-4 text-xs text-[#a1a1a1]">
                <div className="flex items-center gap-1.5">
                  <span className="text-[#707070]">Budget:</span>
                  <select
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(Number(e.target.value))}
                    className="bg-[#121212] border border-[#262626] rounded px-1.5 py-0.5 text-xs text-[#ededed] outline-none cursor-pointer font-mono"
                  >
                    <option value={2048}>2K tokens</option>
                    <option value={4096}>4K tokens</option>
                    <option value={8192}>8K tokens</option>
                  </select>
                </div>

                <label className="flex items-center gap-1.5 cursor-pointer select-none text-xs text-[#a1a1a1] hover:text-[#ededed] transition-colors">
                  <input
                    type="checkbox"
                    checked={includeStructuralGraph}
                    onChange={(e) => setIncludeStructuralGraph(e.target.checked)}
                    className="rounded bg-[#121212] border-[#262626] text-[#ffffff] focus:ring-0"
                  />
                  <span>Include AST Graph</span>
                </label>
              </div>

              {/* Submit Button */}
              <Button type="submit" size="sm" variant="primary" loading={synthesizing} disabled={!taskPrompt.trim()}>
                <span>Synthesize</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </div>

          {/* Preset Suggested Prompts */}
          {suggestedPrompts && suggestedPrompts.length > 0 && (
            <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 scrollbar-none">
              <span className="text-[10px] uppercase font-semibold text-[#707070] shrink-0 mr-1">
                Suggested:
              </span>
              {suggestedPrompts.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setTaskPrompt(p.prompt)}
                  className="shrink-0 text-xs px-2.5 py-1 rounded-md bg-[#0a0a0a] hover:bg-[#121212] border border-[#262626] hover:border-[#404040] text-[#a1a1a1] hover:text-[#ededed] transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}
        </form>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-[#180808] border border-[#451a1a] text-[#f87171] rounded-md text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      {result ? (
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left Column: Evidence Breakdown */}
          <div className="lg:col-span-1 flex flex-col min-h-0">
            <h3 className="text-xs font-semibold text-[#707070] uppercase tracking-wider mb-2.5">
              Evidence & Grounding
            </h3>
            <EvidenceViewer result={result} />
          </div>

          {/* Right Column: Markdown Synthesis Output */}
          <div className="lg:col-span-2 flex flex-col min-h-0">
            <SynthesisOutput
              result={result}
              onSavePackage={() => {
                setPackageName(result.task_summary || "Context Package");
                setSaveModalOpen(true);
              }}
            />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center border border-[#262626] rounded-lg bg-[#0a0a0a]">
          <EmptyState
            icon={<Layers className="w-8 h-8 text-[#707070]" />}
            title="Ready to Generate Context"
            description="Enter a task above or select a prompt suggestion to assemble deterministic call graphs, relevant files, and synthesized context."
          />
        </div>
      )}

      {/* Save Package Modal */}
      <Dialog
        open={saveModalOpen}
        onOpenChange={setSaveModalOpen}
        title="Save Context Package"
        description="Preserve this generated context as a reusable package for IDE extensions and external coding agents."
        maxWidth="sm"
      >
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-[#a1a1a1]">Package Name</label>
            <Input
              value={packageName}
              onChange={(e) => setPackageName(e.target.value)}
              placeholder="e.g. Auth Implementation Context"
              autoFocus
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setSaveModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={savingPackage} disabled={!packageName.trim()}>
              Save Package
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Saved Packages Drawer */}
      <PackageDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSelectPackage={(_markdown) => {
          // Re-populate view with selected package context
        }}
      />
    </div>
  );
};
