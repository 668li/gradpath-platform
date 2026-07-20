import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (className 合并工具)", () => {
  it("应合并多个类名字符串", () => {
    expect(cn("px-2", "py-1")).toBe("px-2 py-1");
  });

  it("应处理条件类名（falsy 值被过滤）", () => {
    expect(cn("base", false && "hidden", undefined, null, "visible")).toBe(
      "base visible",
    );
  });

  it("应解决 Tailwind 类名冲突（后者优先）", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("应处理空输入", () => {
    expect(cn()).toBe("");
  });

  it("应处理对象语法", () => {
    expect(cn({ active: true, disabled: false })).toBe("active");
  });
});
