// 考公流程时间线（feature 001 / M4）— 对齐后端 app/schemas/exam_timeline.py
// 诚实契约：UNKNOWN ⇒ planned_date/predict_basis 必 null（后端响应模型强制）。

export type TimelineDateStatus = "OFFICIAL" | "PREDICTED" | "UNKNOWN";

export interface DarkKnowledgeBrief {
  id: string;
  title: string;
  confidence: string;
}

export interface TimelineNode {
  id: string;
  stage_key: string;
  title: string;
  seq: number;
  date_status: TimelineDateStatus;
  planned_date: string | null;
  planned_end_date: string | null;
  predict_basis: string | null;
  official_entry_url: string | null;
  source_url: string | null;
  collected_at: string | null;
  evidence_id: string | null;
  materials: unknown[];
  action_guide: string;
  verifiable: boolean;
  dark_knowledge: DarkKnowledgeBrief[];
}

export interface NextNodeBrief {
  stage_key: string;
  planned_date: string | null;
  date_status: TimelineDateStatus;
  is_predictive: boolean;
}

export interface TimelineExam {
  id: string;
  code: string;
  name: string;
  track: string;
  year: number;
  status: string;
  official_home_url: string;
  next_node: NextNodeBrief | null;
}

export interface TimelineExamDetail extends TimelineExam {
  nodes: TimelineNode[];
}

export interface TimelineProgress {
  reached: number;
  done: number;
  feedback_rate: number | null;
}

export interface MyTimelineExam {
  exam: TimelineExam;
  subscribed: boolean;
  progress: TimelineProgress;
  completion_rate: number | null;
  next_node: NextNodeBrief | null;
}

export type NodeFeedbackStatus = "done" | "uncertain" | "skipped";
