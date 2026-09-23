/**
 * Lightweight In-Memory SWR (Stale-While-Revalidate) Query Cache for RE:Track.
 * Eliminates duplicate IPC roundtrips, enables instant tab switching,
 * and supports speculative pre-fetching on hover.
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  inFlightPromise?: Promise<T>;
}

class QueryCacheManager {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private defaultStaleTimeMs: number = 30_000; // 30 seconds
  private defaultCacheTimeMs: number = 300_000; // 5 minutes

  /**
   * Fetch data with SWR caching.
   * If fresh cached data exists, returns immediately (< 1ms).
   * If stale data exists, returns stale data immediately while revalidating in background.
   */
  async fetchWithCache<T>(
    key: string,
    fetcher: () => Promise<T>,
    options: {
      staleTimeMs?: number;
      cacheTimeMs?: number;
      forceRefresh?: boolean;
      onBackgroundRevalidate?: (freshData: T) => void;
    } = {}
  ): Promise<T> {
    const {
      staleTimeMs = this.defaultStaleTimeMs,
      cacheTimeMs = this.defaultCacheTimeMs,
      forceRefresh = false,
      onBackgroundRevalidate,
    } = options;

    const now = Date.now();
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;

    // 1. Valid Fresh Cache Hit
    if (entry && !forceRefresh) {
      const age = now - entry.timestamp;
      const isFresh = age < staleTimeMs;
      if (isFresh) {
        return entry.data;
      }

      // 2. Stale Data Hit within cacheTimeMs -> Return stale data instantly, trigger background revalidation
      if (entry.data !== undefined && age < cacheTimeMs && !entry.inFlightPromise) {
        entry.inFlightPromise = (async () => {
          try {
            const fresh = await fetcher();
            this.cache.set(key, { data: fresh, timestamp: Date.now() });
            if (onBackgroundRevalidate) {
              onBackgroundRevalidate(fresh);
            }
            return fresh;
          } catch (err) {
            console.warn(`[QueryCache] Background revalidation failed for '${key}':`, err);
            return entry.data;
          } finally {
            if (this.cache.has(key)) {
              this.cache.get(key)!.inFlightPromise = undefined;
            }
          }
        })();

        return entry.data;
      }
    }

    // 3. In-flight promise deduplication
    if (entry?.inFlightPromise && !forceRefresh) {
      return entry.inFlightPromise;
    }

    // 4. Cold Fetch
    const inFlightPromise = (async () => {
      try {
        const data = await fetcher();
        this.cache.set(key, { data, timestamp: Date.now() });
        return data;
      } finally {
        if (this.cache.has(key)) {
          this.cache.get(key)!.inFlightPromise = undefined;
        }
      }
    })();

    if (entry) {
      entry.inFlightPromise = inFlightPromise;
    } else {
      this.cache.set(key, {
        data: undefined as any,
        timestamp: 0,
        inFlightPromise,
      });
    }

    return inFlightPromise;
  }

  /**
   * Speculative background pre-fetch. Does not block or throw.
   */
  prefetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    staleTimeMs: number = this.defaultStaleTimeMs
  ): void {
    const entry = this.cache.get(key);
    const now = Date.now();
    if (entry && now - entry.timestamp < staleTimeMs) {
      return; // Already fresh
    }

    if (entry?.inFlightPromise) {
      return; // Already in-flight
    }

    this.fetchWithCache(key, fetcher, { staleTimeMs }).catch(() => {
      // Ignore prefetch errors silently
    });
  }

  /**
   * Invalidate one or more cache keys.
   */
  invalidate(keyOrPrefix?: string): void {
    if (!keyOrPrefix) {
      this.cache.clear();
      return;
    }
    for (const key of this.cache.keys()) {
      if (key.startsWith(keyOrPrefix)) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * Get cache telemetry stats.
   */
  getStats() {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }
}

export const queryCache = new QueryCacheManager();
