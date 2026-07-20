# GradPath Makefile — 简化常用命令
# 使用方法: make <target>

.PHONY: help install dev test lint format migrate migrate-new db-reset security-scan security-bandit security-safety security-audit security-all

# 默认目标
help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ===== 安装 =====
install: ## 安装后端和前端依赖
	cd backend && pip install -e ".[dev]"
	cd frontend && npm ci

install-backend: ## 仅安装后端依赖
	cd backend && pip install -e ".[dev]"

install-frontend: ## 仅安装前端依赖
	cd frontend && npm ci

# ===== 开发服务器 =====
dev: ## 启动后端和前端开发服务器（需要并行运行）
	@echo "请在两个终端分别运行:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

dev-backend: ## 启动后端开发服务器
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## 启动前端开发服务器
	cd frontend && npm run dev

# ===== 测试 =====
test: test-backend test-frontend ## 运行所有测试

test-backend: ## 运行后端测试
	cd backend && pytest tests/ -v

test-frontend: ## 运行前端单元测试
	cd frontend && npm run test

test-e2e: ## 运行前端 E2E 测试（需要后端运行）
	cd frontend && npm run test:e2e

test-coverage: ## 运行测试并生成覆盖率报告
	cd backend && pytest tests/ --cov=app --cov-report=html
	cd frontend && npm run test:coverage

# ===== 代码质量 =====
lint: lint-backend lint-frontend ## 运行所有 linter

lint-backend: ## 后端 lint
	cd backend && ruff check app/ tests/ pipeline/
	cd backend && isort --check-only --diff app/ tests/ pipeline/

lint-frontend: ## 前端 lint
	cd frontend && npm run lint

format: ## 格式化所有代码
	cd backend && black app/ tests/ pipeline/
	cd backend && isort app/ tests/ pipeline/
	cd backend && ruff check --fix app/ tests/ pipeline/
	cd frontend && npm run lint -- --fix

type-check: ## 类型检查
	cd backend && mypy app/
	cd frontend && npx tsc --noEmit

# ===== 数据库 =====
migrate: ## 执行数据库迁移
	cd backend && alembic upgrade head

migrate-new: ## 创建新迁移 (用法: make migrate-new m="描述")
	cd backend && alembic revision --autogenerate -m "$(m)"

migrate-down: ## 回滚一个迁移
	cd backend && alembic downgrade -1

migrate-history: ## 查看迁移历史
	cd backend && alembic history --verbose

db-reset: ## 重置数据库（危险！仅开发环境）
	cd backend && alembic downgrade base && alembic upgrade head

# ===== 安全 =====
security-scan: security-bandit security-safety security-audit ## 运行所有安全扫描

security-bandit: ## Bandit 静态安全分析
	cd backend && pip install bandit -q && bandit -r app/ -f json -o bandit-report.json 2>&1 | tail -5
	@echo "Bandit 扫描完成，报告: backend/bandit-report.json"

security-safety: ## Safety 依赖漏洞检查
	cd backend && pip install safety -q && safety check --output json > safety-report.json 2>&1 || true
	@echo "Safety 检查完成，报告: backend/safety-report.json"

security-audit: ## 依赖安全审计（npm + pip）
	cd backend && pip-audit || true
	cd frontend && npm audit || true

# ===== Pre-commit =====
pre-commit-install: ## 安装 pre-commit hooks
	pre-commit install

pre-commit-run: ## 运行 pre-commit（所有文件）
	pre-commit run --all-files

# ===== 清理 =====
clean: ## 清理构建产物和缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/*.egg-info backend/build backend/dist
	rm -rf frontend/.next frontend/node_modules
	rm -f backend/bandit-report.json
