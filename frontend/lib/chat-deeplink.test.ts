import { describe, expect, it } from "vitest";

import { readChatDeepLink } from "./chat-deeplink";

describe("readChatDeepLink", () => {
  it("解析合法提醒深链（prefill + 白名单 skill）", () => {
    const out = readChatDeepLink(
      "?prefill=%E5%9B%BD%E8%80%83%E6%8A%A5%E5%90%8D%E6%98%8E%E5%A4%A9%E6%88%AA%E6%AD%A2&skill=timeline_companion&src=reminder&node=abc",
    );
    expect(out).toEqual({ prefill: "国考报名明天截止", skill: "timeline_companion" });
  });

  it("skill 不在白名单 ⇒ skill 置 null，prefill 保留", () => {
    const out = readChatDeepLink("?prefill=你好&skill=evil_skill&src=reminder");
    expect(out).toEqual({ prefill: "你好", skill: null });
  });

  it("缺 src=reminder ⇒ 不是合法深链（溯源标记硬校验）", () => {
    expect(readChatDeepLink("?prefill=你好&skill=timeline_companion")).toBeNull();
  });

  it("无 prefill / 空 search ⇒ null", () => {
    expect(readChatDeepLink("?src=reminder")).toBeNull();
    expect(readChatDeepLink("")).toBeNull();
  });

  it("prefill 首尾空白被裁剪", () => {
    const out = readChatDeepLink("?prefill=%20%E4%BD%A0%E5%A5%BD%20&src=reminder");
    expect(out?.prefill).toBe("你好");
  });
});
