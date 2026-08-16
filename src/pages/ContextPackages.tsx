import { useEffect } from "react";
import { FileText, Loader2, Sparkles, Plus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { PackageCard } from "@/components/context-packages/PackageCard";
import { useContextPackageStore } from "@/stores/context-package-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ContextPackages() {
  const { packages, loading, error, fetchPackages } = useContextPackageStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-background">
      <TopBar title="RE:Track | Context Packages" />

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/80 pb-5">
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-bold tracking-tight text-foreground">
                  Saved Context Packages
                </h1>
                <Badge variant="secondary" className="text-xs font-mono">
                  {packages.length} packages
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Persistent markdown packages synthesized for external AI coding agents.
              </p>
            </div>

            <Button
              onClick={() => navigate("/")}
              size="sm"
              className="gap-2 h-9 text-xs font-semibold shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Generate Package</span>
            </Button>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="bg-destructive/10 text-destructive border border-destructive/30 rounded-lg p-3.5 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-xs font-mono text-muted-foreground">
                Loading saved packages...
              </p>
            </div>
          )}

          {/* Empty State */}
          {!loading && packages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center bg-card/40 rounded-xl border border-border/70 p-8">
              <div className="w-12 h-12 rounded-xl bg-secondary/80 flex items-center justify-center mb-3">
                <FileText className="w-6 h-6 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">
                No context packages saved yet
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mt-1 mb-4">
                Intercept developer tasks in Context Studio to synthesize and deliver structured context packages.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate("/")}
                className="gap-2 text-xs"
              >
                <Sparkles className="w-3.5 h-3.5 text-primary" />
                <span>Go to Context Studio</span>
              </Button>
            </div>
          )}

          {/* Package List */}
          {!loading && packages.length > 0 && (
            <div className="flex flex-col gap-3.5">
              {packages.map((pkg) => (
                <PackageCard key={pkg.id} pkg={pkg} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
