// frontend/components/__tests__/auth-guard.test.tsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { AuthGuard } from "@/components/auth-guard";

describe("AuthGuard", () => {
  it("渲染 children（兜底层，不阻断）", () => {
    const { getByText } = render(
      <AuthGuard>
        <div>hello world</div>
      </AuthGuard>,
    );
    expect(getByText("hello world")).toBeDefined();
  });

  it("多个子元素均透传", () => {
    const { getByText } = render(
      <AuthGuard>
        <div>first</div>
        <div>second</div>
      </AuthGuard>,
    );
    expect(getByText("first")).toBeDefined();
    expect(getByText("second")).toBeDefined();
  });

  it("null children 也不抛错", () => {
    expect(() => render(<AuthGuard>{null}</AuthGuard>)).not.toThrow();
  });
});
