/**
 * HealthIndicator — shows backend health status as a colored dot.
 */

import { useEffect, useState } from "react";
import { health, HealthResponse } from "../lib/api";

export default function HealthIndicator() {
  const [status, setStatus] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const h = await health();
        setStatus(h);
        setError(false);
      } catch {
        setError(true);
        setStatus(null);
      }
    };

    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  const getColor = () => {
    if (error) return "bg-red-500";
    if (!status) return "bg-yellow-500";
    if (status.status === "ok") return "bg-green-500";
    return "bg-yellow-500";
  };

  const getTooltip = () => {
    if (error) return "Backend unreachable";
    if (!status) return "Checking...";
    if (status.status === "ok") return `Running v${status.version}`;
    return "Degraded";
  };

  return (
    <div className="flex items-center justify-center" title={getTooltip()}>
      <div className={`w-3 h-3 rounded-full ${getColor()}`} />
    </div>
  );
}
