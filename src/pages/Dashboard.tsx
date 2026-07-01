import { useNavigate } from "react-router-dom";
import {
  FolderOpen,
  Sparkles,
  Plus,
  Zap,
  RefreshCw,
} from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { StatCard } from "@/components/shared/StatCard";
import { ActivityTimeline } from "@/components/dashboard/ActivityTimeline";

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <>
      <TopBar />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[1440px] mx-auto">
          {/* Hero */}
          <section className="mb-12 flex flex-col gap-4">
            <h1 className="text-[32px] leading-[40px] tracking-[-0.02em] font-semibold text-on-surface">
              Build Context Packages for AI
            </h1>
            <p className="text-[16px] leading-[24px] text-on-surface-variant max-w-2xl">
              Transform repository knowledge into structured context for coding
              assistants. High-performance, local-first indexing.
            </p>
            <div className="flex items-center gap-4 mt-2">
              <button
                onClick={() => navigate("/repositories")}
                className="bg-primary hover:bg-primary-container text-on-primary px-6 py-2.5 rounded-lg text-[12px] leading-[16px] tracking-[0.02em] font-medium flex items-center gap-2 transition-transform hover:scale-[1.02] shadow-[0_0_15px_rgba(173,198,255,0.2)]"
              >
                <FolderOpen className="w-[18px] h-[18px]" />
                Import Repository
              </button>
              <button
                onClick={() => navigate("/context-builder")}
                className="border border-outline-variant bg-transparent hover:bg-surface-variant text-on-surface px-6 py-2.5 rounded-lg text-[12px] leading-[16px] tracking-[0.02em] font-medium flex items-center gap-2 transition-colors"
              >
                <Zap className="w-[18px] h-[18px]" />
                Generate Context
              </button>
            </div>
          </section>

          {/* Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
            {/* Stats Bento */}
            <div className="md:col-span-8 grid grid-cols-2 lg:grid-cols-3 gap-4">
              <StatCard
                icon={<FolderOpen className="w-4 h-4 text-primary" />}
                label="Indexed Repositories"
                value="12"
                glow
              />
              <StatCard
                icon={<Plus className="w-4 h-4 text-tertiary" />}
                label="Memories Stored"
                value="1.2M"
              />
              <StatCard
                icon={<Sparkles className="w-4 h-4 text-secondary" />}
                label="Packages Generated"
                value="45"
              />
              <StatCard
                icon={<RefreshCw className="w-4 h-4" />}
                label="Avg. Gen Time"
                value="1.4s"
              />
              <StatCard
                icon={<FolderOpen className="w-4 h-4" />}
                label="Avg. Package Size"
                value="12KB"
              />
              <StatCard
                icon={<Zap className="w-4 h-4" />}
                label="Last Indexed"
                value="andes-core"
                isBadge
              />
            </div>

            {/* Activity Timeline */}
            <div className="md:col-span-4">
              <ActivityTimeline />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
