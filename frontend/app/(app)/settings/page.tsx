"use client";

import { useEffect, useState } from "react";
import {
  Download,
  FileSpreadsheet,
  FileText,
  Save,
  UserCircle,
} from "lucide-react";
import { authApi, exportV2Api, useApi } from "@/lib/api";
import { LoadingState } from "@/components/ui/empty";
import { Button, Field, Input, Textarea } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { useAuthStore } from "@/stores/auth";
import type { UserResponse } from "@/types";

export default function SettingsPage() {
  const toast = useToast();
  const setUser = useAuthStore((s) => s.setUser);

  const { data: user, isLoading } = useApi<UserResponse | null>("/api/auth/me");

  const [nickname, setNickname] = useState("");
  const [school, setSchool] = useState("");
  const [major, setMajor] = useState("");
  const [graduationYear, setGraduationYear] = useState("");
  const [bio, setBio] = useState("");
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState<"profile" | "csv" | "json" | null>(null);

  // 加载当前资料后回填表单
  useEffect(() => {
    if (user) {
      setNickname(user.nickname ?? "");
      setSchool(user.school ?? "");
      setMajor(user.major ?? "");
      setGraduationYear(user.graduation_year?.toString() ?? "");
      setBio(user.bio ?? "");
    }
  }, [user]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await authApi.updateMe({
        nickname: nickname.trim() || null,
        school: school.trim() || null,
        major: major.trim() || null,
        graduation_year: graduationYear ? parseInt(graduationYear, 10) : null,
        bio: bio.trim() || null,
      });
      setUser(updated); // 同步侧边栏等处的用户信息
      toast.success("资料已保存");
    } catch {
      toast.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async (type: "profile" | "csv" | "json") => {
    setExporting(type);
    try {
      if (type === "profile") {
        await exportV2Api.profileReport();
        toast.success("画像报告已开始下载");
      } else {
        await exportV2Api.dataExport(type);
        toast.success("数据已导出");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(null);
    }
  };

  if (isLoading) {
    return <LoadingState text="正在加载设置…" />;
  }

  return (
    <div className="space-y-6 max-w-3xl animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink-800">账户设置</h1>
        <p className="mt-1 text-sm text-ink-500">
          修改昵称、院校背景与个人简介。密码与邮箱暂不支持在线修改。
        </p>
      </div>

      {/* 基本资料 */}
      <section className="card p-6 space-y-5">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-ink-800">
          <UserCircle className="h-5 w-5 text-brand-500" /> 基本资料
        </h2>
        <Field label="昵称" hint="展示在社区发言与个人主页">
          <Input
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="你的昵称（可选）"
            maxLength={50}
          />
        </Field>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="学校">
            <Input
              value={school}
              onChange={(e) => setSchool(e.target.value)}
              placeholder="如：某大学"
              maxLength={255}
            />
          </Field>
          <Field label="专业">
            <Input
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              placeholder="如：计算机科学与技术"
              maxLength={255}
            />
          </Field>
        </div>
        <Field label="毕业年份" hint="用于毕业去向与时间线推算">
          <Input
            type="number"
            value={graduationYear}
            onChange={(e) => setGraduationYear(e.target.value)}
            placeholder="如：2028"
            min={1970}
            max={2100}
          />
        </Field>
        <Field label="个人简介" hint="一句话介绍自己（最多 500 字）">
          <Textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="如：大二在读，目标考研上岸计算机硕士。"
            rows={4}
            maxLength={500}
          />
        </Field>
        <div className="flex justify-end">
          <Button onClick={handleSave} loading={saving}>
            <Save className="h-4 w-4" /> 保存资料
          </Button>
        </div>
      </section>

      {/* 数据导出 */}
      <section className="card p-6 space-y-4">
        <h2 className="flex items-center gap-2 font-display text-lg font-semibold text-ink-800">
          <Download className="h-5 w-5 text-brand-500" /> 数据导出
        </h2>
        <p className="text-sm text-ink-500">
          导出你在本平台积累的规划数据，随时可带走。
        </p>
        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            loading={exporting === "profile"}
            onClick={() => handleExport("profile")}
          >
            <FileText className="h-4 w-4" /> 画像报告（PDF）
          </Button>
          <Button
            variant="secondary"
            loading={exporting === "csv"}
            onClick={() => handleExport("csv")}
          >
            <FileSpreadsheet className="h-4 w-4" /> 全部数据（CSV）
          </Button>
          <Button
            variant="secondary"
            loading={exporting === "json"}
            onClick={() => handleExport("json")}
          >
            <FileText className="h-4 w-4" /> 全部数据（JSON）
          </Button>
        </div>
      </section>
    </div>
  );
}
