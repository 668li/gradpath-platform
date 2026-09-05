// frontend/components/assessment/role-match.ts
// 身份覆盖（红线：一切榜单/推荐必须覆盖考研/考公/泛就业/在校等非技术人群）：
// 目标方向为考研/考公的用户，霍兰德 top5 职业适配不应被 IT 角色刷屏——
// 给升学/体制内角色（考研科研/公务员/教师）加成后再排序。

export interface RankableRole {
  role: string;
  match: number;
}

/** 用户目标方向含考研/考公时获得加成的角色 */
const PUBLIC_SERVICE_ROLES = new Set(["考研科研", "公务员", "教师"]);

/** 加成值（拍板默认 15，调整只改这一个常量） */
export const IDENTITY_BOOST = 15;

export function applyIdentityBoost<T extends RankableRole>(
  roles: T[],
  targetDirection: string | null | undefined,
): T[] {
  const wantsPublicPath =
    !!targetDirection &&
    (targetDirection.includes("考研") || targetDirection.includes("考公"));
  if (!wantsPublicPath) return roles;
  return roles.map((r) =>
    PUBLIC_SERVICE_ROLES.has(r.role)
      ? { ...r, match: Math.min(100, r.match + IDENTITY_BOOST) }
      : r,
  );
}

/** 加成 → 按匹配分降序 → 取前 topN（不改动入参数组） */
export function topRoles<T extends RankableRole>(
  roles: T[],
  targetDirection: string | null | undefined,
  topN = 5,
): T[] {
  return applyIdentityBoost(roles, targetDirection)
    .slice()
    .sort((a, b) => b.match - a.match)
    .slice(0, topN);
}
