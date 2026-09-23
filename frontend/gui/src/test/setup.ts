import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// In-memory Storage mock for Zustand persist middleware
const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => (key in store ? store[key] : null)),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = String(value);
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((i: number) => Object.keys(store)[i] || null),
  };
};

const storageMock = createStorageMock();
Object.defineProperty(window, "localStorage", { value: storageMock, writable: true });
Object.defineProperty(global, "localStorage", { value: storageMock, writable: true });
Object.defineProperty(window, "sessionStorage", { value: createStorageMock(), writable: true });

// Polyfill window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Polyfill ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Polyfill IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
};

// Polyfill window.scrollTo
window.scrollTo = vi.fn();

// Polyfill navigator.clipboard with configurable: true so userEvent can attach
Object.defineProperty(navigator, "clipboard", {
  configurable: true,
  writable: true,
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
    readText: vi.fn().mockResolvedValue(""),
  },
});

// Polyfill window.__TAURI_INTERNALS__ and mock invoke
export type MockInvokeHandler = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
let customHandler: MockInvokeHandler | null = null;
let defaultHandler: MockInvokeHandler | null = null;

export function setCustomMockHandler(handler: MockInvokeHandler | null) {
  customHandler = handler;
}

export function setDefaultMockHandler(handler: MockInvokeHandler | null) {
  defaultHandler = handler;
}

const invokeDispatcher = async (cmd: string, args?: Record<string, unknown>) => {
  if (customHandler) {
    return customHandler(cmd, args);
  }
  if (defaultHandler) {
    return defaultHandler(cmd, args);
  }
  return { success: true };
};

(window as unknown as { __TAURI_INTERNALS__?: Record<string, unknown> }).__TAURI_INTERNALS__ = {
  invoke: vi.fn(invokeDispatcher),
};

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(invokeDispatcher),
}));

// Clean up DOM and mocks after each test
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  storageMock.clear();
  customHandler = null;
});
