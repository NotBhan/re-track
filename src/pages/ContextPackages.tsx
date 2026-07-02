import { useEffect } from "react";
import { FileText, Loader2 } from "lucide-react";
import { TopBar } from "@/components/layout/TopBar";
import { PackageCard } from "@/components/context-packages/PackageCard";
import { useContextPackageStore } from "@/stores/context-package-store";

export default function ContextPackages() {
  const { packages, loading, error, fetchPackages } = useContextPackageStore();

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  return (
    <>
      <TopBar title="Context Packages" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[1440px] mx-auto">
          {/* Page Header */}
          <div className="border-b border-surface-variant pb-4 mb-6">
            <h2 className="text-[32px] leading-[40px] tracking-[-0.02em] font-semibold text-on-surface mb-1">
              Context Packages
            </h2>
            <p className="text-[16px] leading-[24px] text-on-surface-variant">
              View, manage, and export saved context packages.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-error-container text-on-error-container border border-error/30 rounded-xl p-4 text-[14px] mb-4">
              {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
          )}

          {/* Empty State */}
          {!loading && packages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-outline-variant flex items-center justify-center mb-4">
                <FileText className="w-8 h-8 text-on-surface-variant/50" />
              </div>
              <h3 className="text-[18px] leading-[28px] font-medium text-on-surface mb-2">
                No context packages saved yet
              </h3>
              <p className="text-[14px] leading-[20px] text-on-surface-variant max-w-[360px]">
                Generate a context package from the Context Builder and save it to see it here.
              </p>
            </div>
          )}

          {/* Package List */}
          {!loading && packages.length > 0 && (
            <div className="flex flex-col gap-3">
              {packages.map((pkg) => (
                <PackageCard key={pkg.id} pkg={pkg} />
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
