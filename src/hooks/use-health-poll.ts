import { useEffect } from "react";
import { useHealthStore } from "@/stores/health-store";

/**
 * Adaptive health and telemetry polling hook.
 * Automatically pauses when window is minimized / hidden,
 * and refreshes immediately when the user focuses the app.
 */
export function useHealthPoll(intervalMs = 8000) {
  const pollHealth = useHealthStore((s) => s.pollHealth);

  useEffect(() => {
    pollHealth();

    let intervalId: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (!intervalId) {
        intervalId = setInterval(pollHealth, intervalMs);
      }
    };

    const stopPolling = () => {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        pollHealth();
        startPolling();
      }
    };

    startPolling();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [pollHealth, intervalMs]);
}
