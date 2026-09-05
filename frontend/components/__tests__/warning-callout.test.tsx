import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WarningCallout } from "@/components/assessment/warning-callout";

describe("WarningCallout", () => {
  it("有提示时逐条渲染并带作答提示标题", () => {
    render(
      <WarningCallout warnings={["提示一", "提示二"]} />
    );
    expect(screen.getByTestId("answer-warning-callout")).toBeTruthy();
    expect(screen.getByText("作答提示")).toBeTruthy();
    expect(screen.getByText("提示一")).toBeTruthy();
    expect(screen.getByText("提示二")).toBeTruthy();
  });

  it("无提示时渲染 null（不出现在 DOM）", () => {
    const { container } = render(<WarningCallout warnings={[]} />);
    expect(container.querySelector('[data-testid="answer-warning-callout"]')).toBeNull();
  });
});
