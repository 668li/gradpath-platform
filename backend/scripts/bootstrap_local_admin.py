"""引导脚本：在开发库创建本地管理员（用于 research-queue 审核）。

- 幂等：已存在同邮箱用户则复用，仅确保 is_admin=True。
- 密码随机生成（secrets），仅打印一次，不落盘、不入库（库中只存 hash）。
- 走应用自身 ORM + hash_password，参数绑定，无 SQL 拼接。
- 仅供本地开发环境使用，不包含任何个人数据。
"""

import secrets
import sys
from pathlib import Path

# 将 backend/ 加入 sys.path，确保能导入 app.*（与 migrations/env.py 一致）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import User

EMAIL = "localadmin@gradpath.com"
# 邮箱校验拒绝 .local 保留 TLD（API 登录校验）；清理误建的 .local 空壳账号
ORPHAN_EMAIL = "localadmin@gradpath.local"


def main() -> None:
    password = secrets.token_urlsafe(18)
    with SessionLocal() as db:
        orphan = db.query(User).filter(User.email == ORPHAN_EMAIL).first()
        if orphan is not None:
            db.delete(orphan)
            db.commit()
            print("removed orphan .local admin")
        user = db.query(User).filter(User.email == EMAIL).first()
        if user is None:
            user = User(
                email=EMAIL,
                password_hash=hash_password(password),
                name="本地管理员",
                is_admin=True,
            )
            db.add(user)
            db.commit()
            print(f"created admin user id={user.id}")
        else:
            if not user.is_admin:
                user.is_admin = True
                db.commit()
                print(f"promoted existing user id={user.id} to admin")
            else:
                print(f"admin already exists id={user.id}")
        print("email:", EMAIL)
        print("password:", password)


if __name__ == "__main__":
    main()
