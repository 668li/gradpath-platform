# 安全事件报告：LLM API Key 泄漏

> **事件编号**：SECURITY-LLM-LEAK-001
> **发现日期**：2026-07-20
> **严重级别**：高（High）
> **影响范围**：DashScope / DeepSeek LLM API Key 泄漏
> **状态**：待用户处置（本文档为修复指南，不会自动执行任何破坏性操作）

---

## 1. 事件摘要

在仓库 `backend/.env.testbak` 文件中发现硬编码的真实 DashScope / DeepSeek LLM API Key（以 `sk-ws-` 开头）。该文件可能已被 git 跟踪并推送到远程仓库，存在被滥用产生 API 调用费用、数据外泄和账户被盗用的风险。

**泄漏文件**：
- `backend/.env.testbak`（第 6 行 `LLM_API_KEY=sk-ws-...`）

**泄漏密钥特征**：
- 前缀：`sk-ws-`
- 服务方：阿里云 DashScope（兼容 DeepSeek 模型调用）
- 模型：`deepseek-v4-flash`
- Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1/`

---

## 2. 立即行动项（用户必须执行）

> ⚠️ **以下操作必须由仓库所有者本人完成，AI 代理不会代为执行。**

### 2.1 吊销泄漏的 API Key（最高优先级，5 分钟内完成）

1. 登录 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/apiKey)
2. 在「API-KEY 管理」页面定位到泄漏的 Key（以 `sk-ws-` 开头）
3. 点击「删除」或「禁用」该 Key，**立即**使其失效
4. 检查该 Key 的近期调用记录，确认是否有异常调用（非常用模型、异常高峰、异地 IP）
5. 如发现异常调用费用，联系阿里云工单申报

### 2.2 生成新的 API Key

1. 在 DashScope 控制台点击「创建新的 API-KEY」
2. 复制新 Key（仅显示一次，妥善保存）
3. **不要**将新 Key 写入任何 `.env*` 文件并提交到 git
4. 通过以下任一安全方式配置：
   - **本地开发**：写入 `backend/.env`（已被 `.gitignore` 忽略），或使用 PowerShell `$env:LLM_API_KEY`
   - **生产部署**：使用 Docker secrets / Kubernetes Secrets / 阿里云 ASM 等密钥管理服务
   - **CI/CD**：使用 GitHub Actions Secrets（`Settings → Secrets and variables → Actions`）

### 2.3 确认新 Key 已生效

```powershell
# 在 backend 目录下验证（不要把 Key 写入命令历史）
$env:LLM_API_KEY = "<新Key>"
python -c "import os; from app.services.ai_service import AIService; svc = AIService(); print(svc.health_check())"
```

---

## 3. Git History 清理指南

> ⚠️ **此节操作为破坏性 git 操作，必须由用户授权后执行。AI 代理不会代为执行。**
>
> 强烈建议先备份仓库：`git clone --mirror <repo-url> repo-backup.git`

### 3.1 检查泄漏是否进入 git history

```powershell
# 查看 .env.testbak 是否被 git 跟踪过
git log --all --full-history -- backend/.env.testbak

# 在所有历史提交中搜索泄漏的 Key 前缀（注意会输出敏感内容，执行后清理终端）
git log -p -S "sk-ws-" --all --source
```

如以上命令无输出，说明文件从未被提交，**仅需完成第 2 节即可**，跳过本节。

### 3.2 使用 git filter-repo 清理 history（推荐）

`git filter-repo` 是 `git filter-branch` 的官方推荐替代品，速度更快、更安全。

**前置准备**：
```powershell
# 安装 git-filter-repo
pip install git-filter-repo

# 验证安装
git filter-repo --version
```

**清理方案 A：仅删除泄漏文件**（推荐，影响面最小）
```powershell
# 在仓库根目录执行
cd d:\职业规划\职业规划

# 备份当前状态
git tag pre-filter-backup

# 从所有历史提交中移除泄漏文件
git filter-repo --invert-paths --path backend/.env.testbak --force
```

**清理方案 B：替换泄漏字符串为占位符**（保留文件，仅脱敏）
```powershell
# 创建替换规则文件
@"
sk-ws-H.EMIHEPH.qhkC.MEUCID5Hw7GWpnshmXLih9MjBDn4jr6FDyQeMMjH0ERH1Gm5AiEA2_dp4LguYrmCq4zdpNxRGalGSXl4Zj7iacADfBWI8J4==>REDACTED_API_KEY
"@ | Set-Content -Encoding utf8 replacements.txt

git filter-repo --replace-text replacements.txt --force

# 清理临时文件
Remove-Item replacements.txt
```

### 3.3 强制推送清理后的 history

```powershell
# 查看远程仓库地址
git remote -v

# 强制推送（覆盖远程历史）
# ⚠️ 此操作不可逆，且会影响所有协作者
git push origin --force --all
git push origin --force --tags

# 通知所有协作者重新 clone 仓库，不要 pull
```

### 3.4 清理 GitHub 缓存

即使强制推送后，GitHub 仍可能缓存旧 commit。需执行：
1. 访问仓库 `Settings → General → Danger Zone`
2. 如有敏感 PR/Issue 引用了旧 commit，联系 GitHub Support 请求清理缓存
3. 提交链接：https://github.com/contact

### 3.5 重建本地 clone（推荐）

清理完成后，建议删除本地仓库并重新 clone，避免本地残留引用：
```powershell
# 备份未提交的修改
git stash

# 删除本地仓库（仅当确认远程已清理干净）
# 注意：此操作不可逆
Remove-Item -Recurse -Force d:\职业规划\职业规划

# 重新 clone
git clone <repo-url> d:\职业规划\职业规划
```

---

## 4. 未来预防措施

### 4.1 启用 pre-commit 密钥扫描（已配置）

仓库根目录 `.pre-commit-config.yaml` 已添加 [gitleaks](https://github.com/gitleaks/gitleaks) hook。所有开发者需执行：

```powershell
pip install pre-commit
cd d:\职业规划\职业规划
pre-commit install
pre-commit run gitleaks --all-files
```

启用后，每次 `git commit` 都会自动扫描密钥泄漏。如检测到敏感信息，提交将被拒绝。

### 4.2 GitHub Actions CI 集成（可选但推荐）

仓库已存在 `.github/workflows/security.yml`，建议追加 gitleaks 扫描任务：

```yaml
# 在 .github/workflows/security.yml 中追加
- name: Gitleaks Secret Scanning
  uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 4.3 .gitignore 规则（已加固）

`.gitignore` 已添加以下规则，防止环境备份文件被误提交：
```
.env.testbak
.env.bak
.env.*.bak
.env.*.backup
.env.*.testbak
.env.*.snapshot
```

### 4.4 开发规范

- **绝不要**将真实 API Key 写入 `.env.example`（仅放占位符，如 `<your-api-key>`）
- **绝不要**通过聊天工具/邮件/截图传递 API Key
- 临时测试用 Key 也应通过环境变量传入，不要写入文件
- 定期（每季度）轮换 API Key
- 为不同环境（开发/测试/生产）使用不同的 API Key，并设置调用配额上限

### 4.5 应急联系

如再次发现密钥泄漏：
1. 立即在云厂商控制台吊销 Key
2. 评估是否需要清理 git history
3. 通知所有协作者
4. 在本文档追加事件记录

---

## 5. 本次修复记录（2026-07-20）

| 项目 | 状态 | 文件 |
|------|------|------|
| `.gitignore` 添加 `.env.testbak` 与备份通配规则 | ✅ 已完成 | `.gitignore` |
| `.pre-commit-config.yaml` 添加 gitleaks hook | ✅ 已完成 | `.pre-commit-config.yaml` |
| 创建 `SECURITY.md` 文档 | ✅ 已完成 | `docs/SECURITY.md` |
| 全仓库扫描 `sk-` 前缀可疑字符串 | ✅ 已完成 | 见下表 |
| 删除 `.env.testbak` 文件 | ❌ 未执行（保留作证据） | `backend/.env.testbak` |
| 执行 `git filter-repo` 清理 history | ❌ 未执行（需用户授权） | 见第 3 节 |

### 5.1 全仓库可疑文件扫描结果

使用 Grep 搜索 `sk-[A-Za-z0-9_.-]{20,}` 模式（覆盖 `sk-` 前缀的真实密钥特征）扫描结果：

| 文件路径 | 状态 | 处置建议 |
|---------|------|---------|
| `backend/.env.testbak` | 🔴 包含泄漏的 DashScope Key | 已加入 `.gitignore`，建议保留作证据或由用户决定删除 |

**其他文件均未检测到 `sk-` 前缀的疑似密钥字符串。**

### 5.2 待用户执行的关键操作清单

- [ ] 在 DashScope 控制台吊销泄漏的 Key（见 2.1）
- [ ] 生成新 Key 并通过环境变量配置（见 2.2）
- [ ] 执行 `git log --all --full-history -- backend/.env.testbak` 确认是否进入 history
- [ ] 如已进入 history，按第 3 节执行 `git filter-repo` 清理
- [ ] 安装 pre-commit 并运行 `pre-commit run gitleaks --all-files`
- [ ] 通知协作者（如有）

---

## 参考资料

- [git-filter-repo 官方文档](https://htmlpreview.github.io/?https://github.com/newren/git-filter-repo/blob/docs/html/git-filter-repo.html)
- [GitHub 移除敏感数据指南](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Gitleaks 配置参考](https://github.com/gitleaks/gitleaks#configuration)
- [阿里云 DashScope API Key 管理](https://help.aliyun.com/zh/dashscope/developer-api-key-operations)
