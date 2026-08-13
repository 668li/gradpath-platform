"""管理员密码重置脚本（本地/容器内手动运维用）。

用法:
    RESET_PASSWORD='<新密码>' python reset_pass.py user@example.com [user2@example.com ...]

要求:
    - 密码通过环境变量 RESET_PASSWORD 注入，禁止硬编码（与 SECRET_KEY 同等对待）。
    - 邮箱通过命令行参数传入，不内置任何账户。
"""
import sys
import os
from pathlib import Path

# 以本文件所在目录为基准加入 sys.path，兼容本地与容器内运行（不硬编码 /app）
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> int:
    emails = [a for a in sys.argv[1:] if not a.startswith("-")]
    new_password = os.getenv("RESET_PASSWORD", "")

    if not emails:
        print("用法: RESET_PASSWORD='<新密码>' python reset_pass.py user@example.com [...]")
        return 2
    if not new_password:
        print("错误: 必须通过环境变量 RESET_PASSWORD 提供新密码（禁止硬编码）")
        return 2

    db = SessionLocal()
    try:
        updated = 0
        for email in emails:
            u = db.query(User).filter(User.email == email).first()
            if u:
                u.password_hash = hash_password(new_password)
                print(f"Reset password for {email}")
                updated += 1
            else:
                print(f"User {email} not found")
        db.commit()
        print(f"Done: {updated}/{len(emails)} updated")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
