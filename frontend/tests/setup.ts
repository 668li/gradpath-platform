import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// 每个测试后自动清理 DOM
afterEach(() => {
  cleanup();
});

// Mock next/navigation（App Router 中的路由 hook）
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  redirect: vi.fn(),
}));

// Mock next/font/google（避免在测试环境中加载字体）
vi.mock("next/font/google", () => ({
  Fraunces: () => ({ variable: "--font-display" }),
  Plus_Jakarta_Sans: () => ({ variable: "--font-sans" }),
}));

// Mock localStorage（jsdom 提供，但需要确保类型正确）
// 使用真实存储行为的 mock：setItem 写入、getItem 读取、clear 清空
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => (key in localStorageStore ? localStorageStore[key] : null)),
  setItem: vi.fn((key: string, value: string) => {
    localStorageStore[key] = String(value);
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageStore[key];
  }),
  clear: vi.fn(() => {
    for (const k of Object.keys(localStorageStore)) delete localStorageStore[k];
  }),
  key: vi.fn((index: number) => Object.keys(localStorageStore)[index] ?? null),
  get length() {
    return Object.keys(localStorageStore).length;
  },
};
Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// Mock matchMedia（组件中可能用于响应式判断）
Object.defineProperty(window, "matchMedia", {
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
  writable: true,
});

// Mock IntersectionObserver（用于懒加载组件）
class MockIntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds = [];
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
}
Object.defineProperty(window, "IntersectionObserver", {
  value: MockIntersectionObserver,
  writable: true,
});

// Mock ResizeObserver（Recharts 等图表库依赖）
class MockResizeObserver {
  disconnect() {}
  observe() {}
  unobserve() {}
}
Object.defineProperty(window, "ResizeObserver", {
  value: MockResizeObserver,
  writable: true,
});
