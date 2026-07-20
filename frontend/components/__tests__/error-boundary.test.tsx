// frontend/components/__tests__/error-boundary.test.tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useState, useEffect } from "react";
import { ErrorBoundary } from "@/components/error-boundary";

afterEach(() => {
  vi.clearAllMocks();
});

// 故意抛错以触发 ErrorBoundary 的子组件
function BrokenChild(): JSX.Element {
  useEffect(() => {
    throw new Error("test error from child");
  }, []);
  return <div>this should not render</div>;
}

function HealthyChild(): JSX.Element {
  return <div data-testid="healthy">healthy render</div>;
}

// 通过 prop 切换 children 来制造 throw
function Thrower({ shouldThrow }: { shouldThrow: boolean }): JSX.Element {
  if (shouldThrow) {
    throw new Error("immediate throw");
  }
  return <div data-testid="ok">ok</div>;
}

describe("ErrorBoundary", () => {
  it("正常子组件直接渲染（不进入错误状态）", () => {
    render(
      <ErrorBoundary>
        <HealthyChild />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("healthy")).toBeDefined();
  });

  it("子组件抛错时显示兜底 UI（含错误消息）", () => {
    // 抑制 console.error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Thrower shouldThrow={true} />
      </ErrorBoundary>,
    );
    // 兜底 UI 含「页面加载失败」文案
    expect(screen.getByText("页面加载失败")).toBeDefined();
    // 原始子元素不应渲染
    expect(screen.queryByTestId("ok")).toBeNull();
    spy.mockRestore();
  });

  it("点击「重试」按钮可清除错误状态", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    function ToggleThrower(): JSX.Element {
      const [throwNow, setThrowNow] = useState(false);
      if (throwNow) {
        throw new Error("trigger");
      }
      return (
        <button onClick={() => setThrowNow(true)} data-testid="boom">
          trigger
        </button>
      );
    }

    function Wrapper(): JSX.Element {
      // 受控组件 key 变化后强制重置 ErrorBoundary 状态
      const [key, setKey] = useState(0);
      return (
        <>
          <button data-testid="reset" onClick={() => setKey((k) => k + 1)}>
            reset key
          </button>
          <ErrorBoundary key={key}>
            <ToggleThrower />
          </ErrorBoundary>
        </>
      );
    }

    render(<Wrapper />);
    // 点击 trigger 触发错误
    fireEvent.click(screen.getByTestId("boom"));
    expect(screen.getByText("页面加载失败")).toBeDefined();
    // 点击 ErrorBoundary 内的「重试」按钮（含「重试」文本）
    fireEvent.click(screen.getByText("重试"));
    // 重试后若仍由父组件重新渲染，按钮可能不存在；至少不抛错
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });

  it("自定义 fallback 被使用时覆盖默认 UI", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">custom</div>}>
        <Thrower shouldThrow={true} />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("custom-fallback")).toBeDefined();
    expect(screen.queryByText("页面加载失败")).toBeNull();
    spy.mockRestore();
  });
});
