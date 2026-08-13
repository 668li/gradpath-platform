"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import type { DashboardOverview } from "@/types";
import type { MicroActionPlanResponse } from "@/types/micro-action";

// ===== 职业星系可视化 =====

interface GalaxyPlanet {
  key: string;
  label: string;
  size: number;
  distance: number;
  href: string;
  pathKey: string;
  destinationType: string;
  angle: number;
}

/** 预设 6 颗行星：大小=适配度，距离=实现难度 */
const GALAXY_PLANETS: GalaxyPlanet[] = [
  { key: "kaoyan", label: "考研", size: 80, distance: 120, href: "/kaoyan", pathKey: "kaoyan", destinationType: "postgrad", angle: 330 },
  { key: "employment", label: "就业", size: 90, distance: 100, href: "/employment", pathKey: "employment", destinationType: "employment", angle: 270 },
  { key: "civil-service", label: "考公", size: 70, distance: 150, href: "/civil-service", pathKey: "civil_service", destinationType: "civil_service", angle: 30 },
  { key: "abroad", label: "留学", size: 60, distance: 180, href: "/explore", pathKey: "abroad", destinationType: "abroad", angle: 90 },
  { key: "startup", label: "创业", size: 50, distance: 200, href: "/career-simulator", pathKey: "startup", destinationType: "startup", angle: 150 },
  { key: "gap-year", label: "间隔年", size: 40, distance: 220, href: "/life-design", pathKey: "gap_year", destinationType: "gap_year", angle: 210 },
];

type PlanetState = "green" | "yellow" | "gray";

/** 根据用户数据判定行星状态：绿=已在探索，黄=进行中，灰=待探索 */
function getPlanetState(
  planet: GalaxyPlanet,
  timeline: DashboardOverview["timeline"],
  latestDecision: DashboardOverview["latest_decision"],
  microPlan: MicroActionPlanResponse | null,
): PlanetState {
  const hasDecision =
    timeline.some(
      (t) =>
        t.type === "decision" &&
        (t.title === planet.destinationType ||
          t.title === `去向决策: ${planet.destinationType}`),
    ) || latestDecision?.destination_type === planet.destinationType;
  if (hasDecision) return "green";
  if (microPlan?.status === "active" && microPlan?.target_path === planet.pathKey) {
    return "yellow";
  }
  return "gray";
}

const PLANET_STATE_COLOR: Record<PlanetState, string> = {
  green: "#10b981",
  yellow: "#f59e0b",
  gray: "#94a3b8",
};

const PLANET_STATE_LABEL: Record<PlanetState, string> = {
  green: "已在探索中",
  yellow: "进行中",
  gray: "待探索",
};

/** 难度标签：基于轨道距离 */
function getDifficultyLabel(distance: number): string {
  if (distance < 130) return "中等";
  if (distance < 170) return "较高";
  return "高";
}

/** 职业星系卡片：用户为中心恒星，6 颗职业行星围绕，可点击探索 */
export function CareerGalaxy({
  timeline,
  latestDecision,
  microPlan,
}: {
  timeline: DashboardOverview["timeline"];
  latestDecision: DashboardOverview["latest_decision"];
  microPlan: MicroActionPlanResponse | null;
}) {
  const router = useRouter();
  const [hovered, setHovered] = useState<GalaxyPlanet | null>(null);

  const centerX = 260;
  const centerY = 190;
  const orbitFlatten = 0.55;

  // 预计算行星位置
  const planetPositions = GALAXY_PLANETS.map((p) => {
    const rad = (p.angle * Math.PI) / 180;
    const x = centerX + p.distance * Math.cos(rad);
    const y = centerY + p.distance * orbitFlatten * Math.sin(rad);
    const radius = Math.max(7, p.size / 7 + 2);
    const state = getPlanetState(p, timeline, latestDecision, microPlan);
    return { planet: p, x, y, radius, state };
  });

  return (
    <section className="card p-5 animate-fade-in">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-50 text-purple-600">
          <Sparkles className="h-4 w-4" />
        </div>
        <h2 className="font-display font-semibold text-ink-800">职业星系</h2>
        <span className="text-xs text-ink-400">以你为中心，探索职业方向</span>
      </div>

      {/* 图例 */}
      <div className="mb-2 flex items-center gap-4 text-xs text-ink-500">
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: PLANET_STATE_COLOR.green }} />
          已在探索
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: PLANET_STATE_COLOR.yellow }} />
          进行中
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: PLANET_STATE_COLOR.gray }} />
          待探索
        </span>
      </div>

      <div className="relative">
        <svg viewBox="0 0 520 380" className="w-full" style={{ maxHeight: 380 }}>
          {/* 轨道椭圆 */}
          {GALAXY_PLANETS.map((p) => (
            <ellipse
              key={`orbit-${p.key}`}
              cx={centerX}
              cy={centerY}
              rx={p.distance}
              ry={p.distance * orbitFlatten}
              fill="none"
              stroke="#e2e8f0"
              strokeWidth={1}
              strokeDasharray="3 4"
            />
          ))}

          {/* 中心恒星 */}
          <circle cx={centerX} cy={centerY} r={26} fill="#fef3c7" opacity={0.4} />
          <circle cx={centerX} cy={centerY} r={18} fill="#f59e0b" />
          <circle cx={centerX} cy={centerY} r={18} fill="url(#starGlow)" />
          <text
            x={centerX}
            y={centerY + 4}
            textAnchor="middle"
            className="fill-white"
            style={{ fontSize: 11, fontWeight: 700 }}
          >
            我
          </text>
          <defs>
            <radialGradient id="starGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </radialGradient>
          </defs>

          {/* 行星：onClick 跳转，hover 显示 tooltip */}
          {planetPositions.map(({ planet, x, y, radius, state }) => (
            <g key={planet.key}>
              <circle
                cx={x}
                cy={y}
                r={radius + 6}
                fill="transparent"
                className="cursor-pointer"
                onMouseEnter={() => setHovered(planet)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => router.push(planet.href)}
              />
              <circle
                cx={x}
                cy={y}
                r={radius}
                fill={PLANET_STATE_COLOR[state]}
                className="cursor-pointer transition-all"
                style={{ filter: hovered?.key === planet.key ? "brightness(1.15)" : "none" }}
                onMouseEnter={() => setHovered(planet)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => router.push(planet.href)}
              />
              <text
                x={x}
                y={y + radius + 14}
                textAnchor="middle"
                className="fill-ink-600 pointer-events-none"
                style={{ fontSize: 11, fontWeight: 500 }}
              >
                {planet.label}
              </text>
            </g>
          ))}
        </svg>

        {/* 自定义 tooltip */}
        {hovered && (
          <div
            className="pointer-events-none absolute left-1/2 top-2 -tranink-x-1/2 rounded-lg bg-ink-800 px-3 py-2 text-xs text-white shadow-lg"
            style={{ zIndex: 10 }}
          >
            {(() => {
              const pos = planetPositions.find((p) => p.planet.key === hovered.key);
              const state = pos?.state ?? "gray";
              return (
                <p>
                  <span className="font-semibold">{hovered.label}</span>
                  {" — "}
                  适配度{hovered.size}% — 难度{getDifficultyLabel(hovered.distance)} — {PLANET_STATE_LABEL[state]} — 点击探索
                </p>
              );
            })()}
          </div>
        )}
      </div>
    </section>
  );
}
