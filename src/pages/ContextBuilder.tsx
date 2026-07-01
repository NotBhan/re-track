import { TopBar } from "@/components/layout/TopBar";
import { InputParameters } from "@/components/context-builder/InputParameters";
import { PipelineVisualization } from "@/components/context-builder/PipelineVisualization";
import { OutputPanel } from "@/components/context-builder/OutputPanel";

export default function ContextBuilder() {
  return (
    <>
      <TopBar title="Context Builder" />
      <main className="flex-1 flex overflow-hidden p-6 gap-6">
        <InputParameters />
        <PipelineVisualization />
        <OutputPanel />
      </main>
    </>
  );
}
