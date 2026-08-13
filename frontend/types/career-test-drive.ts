// frontend/types/career-test-drive.ts
// 职业试驾 — 第一人称一日体验类型定义

export interface TimeBlock {
  time: string; // "08:30"
  activity: string; // "晨会"
  description: string; // 详细描述
  emotion: string; // "专注" / "疲惫" / "兴奋"
}

export interface CareerTestDrive {
  id: string;
  path_type: string; // kaoyan / employment / civil_service
  target_role: string; // 如 "互联网产品经理"
  experience_content: TimeBlock[];
  summary: string;
  pros: string[];
  cons: string[];
  created_at: string;
}

export interface CareerTestDriveCreate {
  path_type: string;
  target_role: string;
}
