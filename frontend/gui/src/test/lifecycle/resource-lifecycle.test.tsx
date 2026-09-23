/**
 * Frontend resource-lifecycle regression tests.
 *
 * WebView heap is not deterministically measurable under jsdom, so these tests
 * account for the concrete resources a component can outlive itself with:
 *   - interval timers (polling / schedulers)
 *   - document & window event listeners
 *   - retained derived-storage payloads in global stores
 *
 * The invariant under test is *non-accumulation*: repeated mount/unmount and
 * repeated navigation must not increase the number of live resources. A single
 * shared library singleton (e.g. the motion frameloop scheduler) is permitted,
 * but a growing ledger is a leak.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act } from "@testing-library/react";
import App from "@/App";
import Workspace from "@/pages/Workspace";
import ContextStudio from "@/pages/ContextStudio";
import Memory from "@/pages/Memory";
import SystemTelemetry from "@/pages/SystemTelemetry";
import { renderWithProviders, resetAllStores, mockRepositories } from "@/test/test-utils";
import { useRepositoryStore } from "@/stores/repository-store";
import { useMemoryStore } from "@/stores/memory-store";
import { queryCache } from "@/lib/query-cache";

function installLedger() {
  const liveIntervals = new Set<unknown>();
  const liveListeners = new Map<string, Set<unknown>>();

  const realSetInterval = globalThis.setInterval;
  const realClearInterval = globalThis.clearInterval;
  const realDocAdd = document.addEventListener.bind(document);
  const realDocRemove = document.removeEventListener.bind(document);
  const realWinAdd = window.addEventListener.bind(window);
  const realWinRemove = window.removeEventListener.bind(window);

  globalThis.setInterval = ((...args: Parameters<typeof setInterval>) => {
    const id = realSetInterval(...args);
    liveIntervals.add(id);
    return id;
  }) as typeof setInterval;

  globalThis.clearInterval = ((id?: ReturnType<typeof setInterval>) => {
    if (id !== undefined) liveIntervals.delete(id);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return realClearInterval(id as any);
  }) as typeof clearInterval;

  const bump = (target: string, type: string, handler: unknown, add: boolean) => {
    const key = `${target}:${type}`;
    const set = liveListeners.get(key) ?? new Set<unknown>();
    if (add) set.add(handler);
    else set.delete(handler);
    liveListeners.set(key, set);
  };

  document.addEventListener = ((type: string, handler: never, ...rest: never[]) => {
    bump("document", type, handler, true);
    return realDocAdd(type, handler, ...rest);
  }) as typeof document.addEventListener;
  document.removeEventListener = ((type: string, handler: never, ...rest: never[]) => {
    bump("document", type, handler, false);
    return realDocRemove(type, handler, ...rest);
  }) as typeof document.removeEventListener;
  window.addEventListener = ((type: string, handler: never, ...rest: never[]) => {
    bump("window", type, handler, true);
    return realWinAdd(type, handler, ...rest);
  }) as typeof window.addEventListener;
  window.removeEventListener = ((type: string, handler: never, ...rest: never[]) => {
    bump("window", type, handler, false);
    return realWinRemove(type, handler, ...rest);
  }) as typeof window.removeEventListener;

  return {
    intervalCount: () => liveIntervals.size,
    listenerCount: () => {
      let total = 0;
      for (const set of liveListeners.values()) total += set.size;
      return total;
    },
    restore() {
      globalThis.setInterval = realSetInterval;
      globalThis.clearInterval = realClearInterval;
      document.addEventListener = realDocAdd;
      document.removeEventListener = realDocRemove;
      window.addEventListener = realWinAdd;
      window.removeEventListener = realWinRemove;
    },
  };
}

const flush = async () => {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
};

describe("Resource lifecycle — repeated mount/unmount does not accumulate", () => {
  beforeEach(() => {
    resetAllStores();
    useRepositoryStore.setState({
      selectedId: "repo-1",
      selected: mockRepositories[0],
      repositories: mockRepositories,
    });
  });

  afterEach(() => {
    resetAllStores();
    queryCache.invalidate();
    vi.restoreAllMocks();
  });

  it("does not accumulate interval timers across repeated App mount/unmount", async () => {
    const probe = installLedger();
    try {
      const cycleCounts: number[] = [];

      for (let cycle = 0; cycle < 6; cycle++) {
        const { unmount } = renderWithProviders(<App />, { withRouter: false });
        await flush();
        unmount();
        await flush();
        cycleCounts.push(probe.intervalCount());
      }

      // motion's shared frameloop scheduler may be created/cancelled lazily, so the
      // raw count can oscillate. The invariant that matters is non-accumulation: a
      // per-mount timer leak would grow linearly with the cycle count.
      const maxLive = Math.max(...cycleCounts);
      expect(maxLive).toBeLessThanOrEqual(2);
      expect(cycleCounts[cycleCounts.length - 1]).toBeLessThanOrEqual(2);
      // No growth trend across the run (first half vs last half).
      const half = Math.floor(cycleCounts.length / 2);
      const firstHalfMax = Math.max(...cycleCounts.slice(0, half));
      const lastHalfMax = Math.max(...cycleCounts.slice(half));
      expect(lastHalfMax).toBeLessThanOrEqual(firstHalfMax + 1);
      expect(useRepositoryStore.getState().pollInterval).toBeNull();
    } finally {
      probe.restore();
    }
  });

  it("does not accumulate document/window listeners across repeated navigation", async () => {
    const probe = installLedger();
    try {
      const pages = [Workspace, ContextStudio, Memory, SystemTelemetry];
      const cycleCounts: number[] = [];

      for (let round = 0; round < 4; round++) {
        for (const Page of pages) {
          const { unmount } = renderWithProviders(<Page />, {
            initialEntries: ["/workspace?repo=repo-1"],
          });
          await flush();
          unmount();
        }
        cycleCounts.push(probe.listenerCount());
      }

      // Every page unmount must release the listeners it registered.
      const afterFirstRound = cycleCounts[0];
      expect(cycleCounts.slice(1)).toEqual(Array(cycleCounts.length - 1).fill(afterFirstRound));
      expect(probe.listenerCount()).toBe(0);
    } finally {
      probe.restore();
    }
  });

  it("stops repository progress polling when the owning view unmounts mid-index", async () => {
    const probe = installLedger();
    try {
      const baseline = probe.intervalCount();

      const { unmount } = renderWithProviders(<Workspace />, {
        initialEntries: ["/workspace?repo=repo-1"],
      });
      await flush();

      await act(async () => {
        useRepositoryStore.getState().pollProgress("repo-1");
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
      expect(probe.intervalCount()).toBeGreaterThan(baseline);
      expect(useRepositoryStore.getState().pollInterval).not.toBeNull();

      unmount();
      await flush();

      // The store owns the handle, so a surviving timer would be orphaned.
      expect(probe.intervalCount()).toBe(baseline);
      expect(useRepositoryStore.getState().pollInterval).toBeNull();
    } finally {
      probe.restore();
    }
  });

  it("retains only one derived-storage payload regardless of how many repositories are selected", async () => {
    // Guards against a per-repository graph/vector payload map growing without bound.
    for (let i = 0; i < 12; i++) {
      act(() => {
        useMemoryStore.getState().selectDataset(`ds-${i}`);
      });
      await flush();
    }

    const state = useMemoryStore.getState();
    expect(Array.isArray(state.graph)).toBe(false);
    expect(Array.isArray(state.vectors)).toBe(false);
    // Exactly one active selection is tracked; no history of prior repositories.
    expect(state.selectedDatasetId).toBe("ds-11");
  });
});
