import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// The GUI interface lives under frontend/gui (see frontend/AGENTS.md).
//
// Force the test environment regardless of the ambient shell value: when
// NODE_ENV=production leaks in, Vite resolves the production React build which
// does not export `act`, and every @testing-library render fails.
process.env.NODE_ENV = "test";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    env: { NODE_ENV: "test" },
    setupFiles: ["./frontend/gui/src/test/setup.ts"],
    include: ["frontend/gui/src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./frontend/gui/src"),
    },
  },
});
