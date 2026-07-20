"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Compass, Play, Plus, Trash2, Star, TrendingUp, Shield, AlertTriangle,
  ChevronDown, ChevronRight, BarChart3, Trophy, DollarSign, Heart, Zap,
  GraduationCap, Building2, Briefcase, Landmark, ChevronUp,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, AreaChart, Area,
} from "recharts";
import { careerSimulatorApi } from "@/lib/api";
import type { PathResult, SimulateResponse, Preset, CityTier, Industry } from "@/lib/api/career-simulator";
import { cn } from "@/lib/utils";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { Button, Input, Field } from "@/components/ui/form-controls";

const PATH_ICONS: Record<string, React.ReactNode> = {
  grad_cs: <GraduationCap className="w-5 h-5" />,
  grad_finance: <GraduationCap className="w-5 h-5" />,
  civil_national: <Landmark className="w-5 h-5" />,
  civil_provincial: <Building2 className="w-5 h-5" />,
  career_it: <Briefcase className="w-5 h-5" />,
  career_finance: <Briefcase className="w-5 h-5" />,
  career_education: <Briefcase className="w-5 h-5" />,
  career_healthcare: <Briefcase className="w-5 h-5" />,
  career_fallback: <Briefcase className="w-5 h-5" />,
};

const RISK_COLORS: Record<string, string> = {
  low: "text-green-600 bg-green-50",
  medium: "text-yellow-600 bg-yellow-50",
  high: "text-red-600 bg-red-50",
};

const PATH_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"];

function formatMoney(n: number): string {
  if (n >= 100000000) return (n / 100000000).toFixed(1) + "亿";
  if (n >= 10000) return (n / 10000).toFixed(0) + "万";
  return n.toLocaleString();
}

export default function CareerSimulatorPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [cities, setCities] = useState<CityTier[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  // Path configuration
  const [paths, setPaths] = useState([
    { name: "考研IT", path_type: "grad_cs", city: "Beijing", industry: "IT" },
    { name: "国考", path_type: "civil_national", city: "Hangzhou", industry: "Government" },
    { name: "直接就业", path_type: "career_it", city: "Shenzhen", industry: "IT" },
  ]);
  const [years, setYears] = useState(10);

  // Load presets, cities, industries
  useEffect(() => {
    Promise.all([
      careerSimulatorApi.getPresets(),
      careerSimulatorApi.getCities(),
      careerSimulatorApi.getIndustries(),
    ]).then(([p, c, i]) => {
      setPresets(p.presets || []);
      setCities(c.tiers || []);
      setIndustries(i.industries || []);
    }).catch(() => {});
  }, []);

  const addPath = () => {
    if (paths.length >= 5) return;
    setPaths([...paths, { name: "", path_type: "career_fallback", city: "Beijing", industry: "IT" }]);
  };

  const removePath = (index: number) => {
    if (paths.length <= 1) return;
    setPaths(paths.filter((_, i) => i !== index));
  };

  const updatePath = (index: number, field: string, value: string) => {
    const newPaths = [...paths];
    (newPaths[index] as Record<string, string>)[field] = value;
    setPaths(newPaths);
  };

  const applyPreset = (preset: Preset, index: number) => {
    updatePath(index, "name", preset.name);
    updatePath(index, "path_type", preset.path_type);
    updatePath(index, "city", preset.city);
    updatePath(index, "industry", preset.industry);
  };

  const allCities = [...new Set(cities.flatMap((t) => t.cities))].sort();

  const handleSimulate = async () => {
    if (paths.length === 0) {
      toast.error("请至少添加一个职业路径");
      return;
    }
    setLoading(true);
    try {
      const data = await careerSimulatorApi.simulate({
        current_year: new Date().getFullYear(),
        years,
        paths: paths.map((p) => ({
          name: p.name || "未命名",
          path_type: p.path_type,
          city: p.city,
          industry: p.industry,
        })),
      });
      setResult(data);
      toast.success("模拟完成");
    } catch {
      toast.error("模拟失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (name: string) => {
    const newSet = new Set(expandedPaths);
    if (newSet.has(name)) newSet.delete(name);
    else newSet.add(name);
    setExpandedPaths(newSet);
  };

  // Chart data preparation
  const salaryChartData = result?.paths[0]?.yearly?.map((y, i) => {
    const point: Record<string, number | string> = { year: y.year.toString() };
    result.paths.forEach((p) => {
      point[p.name] = p.yearly[i]?.monthly_salary || 0;
    });
    return point;
  }) || [];

  const satisfactionData = result?.paths.map((p) => ({
    name: p.name,
    satisfaction: p.avg_satisfaction,
    stability: p.stability_score,
    growth: Math.min(p.career_growth_score, 50),
  })) || [];

  const radarData = result?.paths[0]?.yearly?.filter((_, i) => i < 5).map((y, i) => {
    const point: Record<string, number | string> = { dimension: `Year${y.year}` };
    result.paths.forEach((p) => {
      point[p.name] = p.yearly[i]?.satisfaction || 0;
    });
    return point;
  }) || [];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Compass className="w-8 h-8 text-blue-600" />
            职业路径模拟器
          </h1>
          <p className="mt-2 text-gray-500">
            对比不同职业路径的10年发展轨迹 — 薪资、满意度、风险、净收入
          </p>
        </div>

        {/* Path Configuration */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">配置职业路径</h2>
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-500">模拟年数:</label>
              <input
                type="range" min="1" max="10" value={years}
                onChange={(e) => setYears(parseInt(e.target.value))}
                className="w-24"
              />
              <span className="text-sm font-medium w-8">{years}年</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paths.map((path, i) => (
              <div key={`${path.name}-${i}`} className="border rounded-lg p-4 relative bg-gray-50">
                {paths.length > 1 && (
                  <button onClick={() => removePath(i)}
                    className="absolute top-2 right-2 text-gray-400 hover:text-red-500">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <Field label="名称">
                  <Input value={path.name} onChange={(e) => updatePath(i, "name", e.target.value)}
                    placeholder="路径名称" />
                </Field>
                <Field label="类型">
                  <select value={path.path_type} onChange={(e) => updatePath(i, "path_type", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    {industries.flatMap((ind) => ind.paths.map((pt) => (
                      <option key={pt} value={pt}>{ind.name} - {pt}</option>
                    )))}
                  </select>
                </Field>
                <Field label="城市">
                  <select value={path.city} onChange={(e) => updatePath(i, "city", e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm">
                    {allCities.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                {/* Preset quick-fill */}
                <div className="mt-2 flex flex-wrap gap-1">
                  {presets.slice(0, 4).map((p) => (
                    <button key={p.name} onClick={() => applyPreset(p, i)}
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100">
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {paths.length < 5 && (
              <button onClick={addPath}
                className="border-2 border-dashed rounded-lg p-4 flex flex-col items-center justify-center text-gray-400 hover:text-blue-500 hover:border-blue-300 min-h-[200px]">
                <Plus className="w-8 h-8 mb-2" />
                添加路径
              </button>
            )}
          </div>

          <div className="mt-6 flex justify-center">
            <Button onClick={handleSimulate} disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg">
              {loading ? "模拟中..." : <><Play className="w-5 h-5 mr-2" /> 开始模拟</>}
            </Button>
          </div>
        </div>

        {/* Loading */}
        {loading && <LoadingState />}

        {/* Results */}
        {!loading && result && (
          <div className="space-y-6">
            {/* Recommendation Banner */}
            {result.recommendation && (
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
                <div className="flex items-center gap-3">
                  <Trophy className="w-8 h-8" />
                  <div>
                    <h2 className="text-2xl font-bold">推荐路径</h2>
                    <p className="text-blue-100 text-lg">{result.recommendation}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {result.paths.map((p, i) => (
                <div key={p.name} className={cn("rounded-xl p-5 shadow-sm border-2",
                  i === 0 ? "border-blue-500 bg-blue-50" : "border-gray-100 bg-white")}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="p-2 rounded-lg bg-blue-100 text-blue-600">
                      {PATH_ICONS[p.path_type] || <Briefcase />}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900">{p.name}</h3>
                      <p className="text-xs text-gray-500">{p.city} | {p.industry}</p>
                    </div>
                    {i === 0 && <Star className="w-5 h-5 text-yellow-500 ml-auto" />}
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-white rounded p-2">
                      <div className="text-gray-500 text-xs">10年总收入</div>
                      <div className="font-bold text-blue-600">{formatMoney(p.total_income)}</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-gray-500 text-xs">净资产</div>
                      <div className="font-bold text-green-600">{formatMoney(p.net_worth_10yr)}</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-gray-500 text-xs">满意度</div>
                      <div className="font-bold">{p.avg_satisfaction}/10</div>
                    </div>
                    <div className="bg-white rounded p-2">
                      <div className="text-gray-500 text-xs">风险</div>
                      <span className={cn("px-2 py-1 rounded-full text-xs font-medium", RISK_COLORS[p.overall_risk])}>
                        {p.overall_risk === "low" ? "低风险" : p.overall_risk === "high" ? "高风险" : "中风险"}
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-600">{p.recommendation}</div>
                </div>
              ))}
            </div>

            {/* Salary Trend Chart */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" /> 月薪趋势
              </h3>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={salaryChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis tickFormatter={(v) => formatMoney(v)} />
                  <Tooltip formatter={(v: number) => formatMoney(v) + "/月"} />
                  <Legend />
                  {result.paths.map((p, i) => (
                    <Line key={p.name} type="monotone" dataKey={p.name}
                      stroke={PATH_COLORS[i % PATH_COLORS.length]}
                      strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Satisfaction & Stability */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Heart className="w-5 h-5 text-red-500" /> 满意度对比
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={satisfactionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 10]} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="satisfaction" fill="#3b82f6" name="满意度" />
                    <Bar dataKey="stability" fill="#10b981" name="稳定性" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-purple-600" /> 收入对比
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={result.paths.map((p) => ({
                    name: p.name,
                    income: p.total_income,
                    cost: p.total_education_cost,
                    net: p.net_worth_10yr,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis tickFormatter={(v) => formatMoney(v)} />
                    <Tooltip formatter={(v: number) => formatMoney(v)} />
                    <Legend />
                    <Bar dataKey="income" fill="#3b82f6" name="总收入" />
                    <Bar dataKey="net" fill="#10b981" name="净资产" />
                    <Bar dataKey="cost" fill="#ef4444" name="教育成本" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Year-by-Year Detail */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-600" /> 年度详情
              </h3>
              {result.paths.map((p) => (
                <div key={p.name} className="mb-4 border rounded-lg">
                  <button onClick={() => toggleExpand(p.name)}
                    className="w-full flex items-center justify-between p-3 hover:bg-gray-50">
                    <span className="font-medium">{p.name} ({p.city})</span>
                    {expandedPaths.has(p.name) ? <ChevronUp /> : <ChevronDown />}
                  </button>
                  {expandedPaths.has(p.name) && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left">年份</th>
                            <th className="px-3 py-2 text-left">阶段</th>
                            <th className="px-3 py-2 text-right">月薪</th>
                            <th className="px-3 py-2 text-right">年薪</th>
                            <th className="px-3 py-2 text-right">累计</th>
                            <th className="px-3 py-2 text-center">满意度</th>
                            <th className="px-3 py-2 text-center">风险</th>
                            <th className="px-3 py-2 text-right">净资产</th>
                          </tr>
                        </thead>
                        <tbody>
                          {p.yearly.map((y) => (
                            <tr key={y.year} className="border-t hover:bg-gray-50">
                              <td className="px-3 py-2 font-medium">{y.year}</td>
                              <td className="px-3 py-2">
                                <div className="text-xs text-gray-500">{y.phase}</div>
                                <div className="text-xs text-gray-400 truncate max-w-[200px]">{y.phase_detail}</div>
                              </td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.monthly_salary)}</td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.annual_income)}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatMoney(y.cumulative_income)}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={cn("px-2 py-1 rounded-full text-xs",
                                  y.satisfaction >= 7 ? "bg-green-100 text-green-700" :
                                  y.satisfaction >= 5 ? "bg-yellow-100 text-yellow-700" :
                                  "bg-red-100 text-red-700")}>
                                  {y.satisfaction}/10
                                </span>
                              </td>
                              <td className="px-3 py-2 text-center">
                                <span className={cn("px-2 py-1 rounded-full text-xs", RISK_COLORS[y.risk_level])}>
                                  {y.risk_level === "low" ? "低" : y.risk_level === "high" ? "高" : "中"}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right">{formatMoney(y.net_worth)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Market Context */}
            {result.market_context && (
              <div className="bg-gray-100 rounded-xl p-4 text-sm text-gray-600">
                <strong>市场参考:</strong> 一线城市平均月薪 {String(result.market_context.avg_salary_tier1 || 12000)} |
                新一线 {String(result.market_context.avg_salary_tier2 || 8000)} |
                二线 {String(result.market_context.avg_salary_tier3 || 6000)} |
                数据来源: {String(result.market_context.source || "GradPath")}
              </div>
            )}
          </div>
        )}

        {!loading && !result && (
          <EmptyState title="配置路径开始模拟" description="选择职业路径、城市和行业，点击模拟按钮查看10年发展轨迹对比" />
        )}
      </div>
    </div>
  );
}
