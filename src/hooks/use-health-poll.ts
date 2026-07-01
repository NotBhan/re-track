import { useEffect } from "react";
import { useHealthStore } from "@/stores/health-store";

export function useHealthPoll(intervalMs = 10000) {
  const pollHealth = useHealthStore((s) => s.pollHealth);

  useEffect(() => {
    pollHealth();
    const interval = setInterval(pollHealth, intervalMs);
    return () => clearInterval(interval);
  }, [pollHealth, intervalMs]);
}
