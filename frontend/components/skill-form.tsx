"use client";

import { useMemo, useState, type FormEvent } from "react";
import { skillsApi } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form-controls";
import type { SkillResponse } from "@/types";

interface SkillFormProps {
  initial?: SkillResponse | null;
  /** 已有技能树（扁平化前），用于选择父节点 */
  tree: SkillResponse[];
  onSaved: (skill: SkillResponse) => void;
  onCancel: () => void;
}

/** 收集节点及其所有子孙的 id */
function collectDescIds(node: SkillResponse): string[] {
  const ids = [node.id];
  node.children?.forEach((c) => ids.push(...collectDescIds(c)));
  return ids;
}

/** 扁平化为 {id, label} 列表（带层级缩进） */
function flattenForSelect(
  nodes: SkillResponse[],
  excludeIds: Set<string>,
  depth = 0,
): { id: string; label: string }[] {
  const out: { id: string; label: string }[] = [];
  nodes.forEach((n) => {
    if (!excludeIds.has(n.id)) {
      out.push({
        id: n.id,
        label: `${"— ".repeat(depth)}${n.name}`,
      });
      if (n.children?.length) {
        out.push(...flattenForSelect(n.children, excludeIds, depth + 1));
      }
    }
  });
  return out;
}

export function SkillForm({ initial, tree, onSaved, onCancel }: SkillFormProps) {
  const toast = useToast();
  const isEdit = !!initial;

  const [name, setName] = useState(initial?.name ?? "");
  const [category, setCategory] = useState(initial?.category ?? "");
  const [level, setLevel] = useState(initial?.level ?? 1);
  const [parentId, setParentId] = useState(initial?.parent_id ?? "");
  const [acquiredDate, setAcquiredDate] = useState(initial?.acquired_date ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [loading, setLoading] = useState(false);

  // 编辑时排除自身及子孙，避免循环引用
  const excludeIds = useMemo(() => {
    if (!initial) return new Set<string>();
    return new Set(collectDescIds(initial));
  }, [initial]);

  const parentOptions = useMemo(
    () => flattenForSelect(tree, excludeIds),
    [tree, excludeIds],
  );

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !category.trim()) {
      toast.push("请填写技能名和分类", "error");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        name: name.trim(),
        category: category.trim(),
        level,
        parent_id: parentId || null,
        acquired_date: acquiredDate || null,
        notes: notes || null,
      };
      const saved = isEdit && initial
        ? await skillsApi.update(initial.id, payload)
        : await skillsApi.create(payload);
      toast.push(isEdit ? "更新成功" : "创建成功", "success");
      onSaved(saved);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="技能名" required>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="如：React"
            required
          />
        </Field>
        <Field label="分类" required>
          <Input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="如：前端 / 后端 / 软技能"
            list="skill-categories"
            required
          />
          <datalist id="skill-categories">
            {[...new Set(tree.flatMap((n) => [n.category]))].map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Field>
      </div>

      <Field label={`掌握程度：${level} / 5`} hint="1=入门，5=精通">
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={level}
          onChange={(e) => setLevel(Number(e.target.value))}
          className="w-full accent-brand-600"
        />
      </Field>

      <Field label="父技能" hint="可选，用于构建技能树层级">
        <Select value={parentId} onChange={(e) => setParentId(e.target.value)}>
          <option value="">无（顶层技能）</option>
          {parentOptions.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </Select>
      </Field>

      <Field label="习得日期">
        <Input
          type="date"
          value={acquiredDate}
          onChange={(e) => setAcquiredDate(e.target.value)}
          max={todayISO()}
        />
      </Field>

      <Field label="备注">
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="补充说明，如学习路径、应用场景…"
          className="min-h-[70px]"
        />
      </Field>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" loading={loading}>
          {isEdit ? "保存修改" : "创建技能"}
        </Button>
      </div>
    </form>
  );
}
