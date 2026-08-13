/**
 * SourceBadge — 外部来源可信度徽章（P2 来源展示）。
 *
 * 业务表（ExperiencePost / KaoyanNews）不落 credibility 字段，仅保留
 * source_url + source_platform；可信度由前端按与后端
 * research_ingestion._infer_credibility 一致的确定性规则推断：
 * - 官方域名（edu.cn / yz.chsi.com.cn / gov.cn）→ official_verified（绿）
 * - 社区平台（bilibili / v2ex / github / zhihu）→ user_reported（蓝）
 * - 其余 → model_inferred（琥珀）
 */
import { Badge } from "@/components/ui/form-controls";

const OFFICIAL_DOMAINS = ["edu.cn", "yz.chsi.com.cn", "gov.cn"];
const COMMUNITY_PLATFORMS = ["bilibili", "v2ex", "github", "zhihu"];

export type CredibilityLevel = "official_verified" | "user_reported" | "model_inferred";

export function inferCredibility(
  sourceUrl: string | null | undefined,
  sourcePlatform?: string,
): CredibilityLevel {
  const hostname = (sourceUrl ?? "").toLowerCase().replace(/^https?:\/\//, "").split("/")[0];
  if (OFFICIAL_DOMAINS.some((d) => hostname === d || hostname.endsWith(`.${d}`))) {
    return "official_verified";
  }
  const platform = (sourcePlatform ?? "").toLowerCase();
  if (
    COMMUNITY_PLATFORMS.includes(platform) ||
    COMMUNITY_PLATFORMS.some((p) => hostname.includes(p))
  ) {
    return "user_reported";
  }
  return "model_inferred";
}

const CREDIBILITY_META: Record<
  CredibilityLevel,
  { label: string; color: "green" | "blue" | "amber"; title: string }
> = {
  official_verified: {
    label: "官方来源",
    color: "green",
    title: "来源为官方域名（edu.cn / 研招网 / gov.cn）",
  },
  user_reported: {
    label: "社区报告",
    color: "blue",
    title: "来源为社区平台（B站 / 知乎 / GitHub 等），信息由用户提供",
  },
  model_inferred: {
    label: "AI 推断",
    color: "amber",
    title: "来源未标注官方或社区，可信度需人工核验",
  },
};

interface SourceBadgeProps {
  sourceUrl?: string | null;
  sourcePlatform?: string;
  /** 同时展示来源平台名（默认 true） */
  showPlatform?: boolean;
  className?: string;
}

export function SourceBadge({ sourceUrl, sourcePlatform, showPlatform = true, className }: SourceBadgeProps) {
  const level = inferCredibility(sourceUrl, sourcePlatform);
  const meta = CREDIBILITY_META[level];
  const platformLabel = sourcePlatform
    ? sourcePlatform === "bilibili"
      ? "B站"
      : sourcePlatform === "xiaohongshu"
        ? "小红书"
        : sourcePlatform
    : "网页";

  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`} title={meta.title}>
      {showPlatform && (
        <Badge color="slate" className="uppercase">
          {platformLabel}
        </Badge>
      )}
      <Badge color={meta.color}>{meta.label}</Badge>
    </span>
  );
}
