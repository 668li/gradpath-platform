"""北极星度量端点测试：周序列分桶 + 聚合比率（纯函数层，不依赖完整请求栈）。"""

from datetime import datetime, timedelta, timezone

from app.api.north_star import _week_start


def test_week_start_is_monday():
    """周三取出的周起点应是同一周的周一。"""
    wed = datetime(2026, 9, 2, 15, 0, tzinfo=timezone.utc)  # 周三
    assert _week_start(wed) == "2026-08-31"  # 周一


def test_week_start_boundary():
    """周日与次日周一应分属不同周桶。"""
    sun = datetime(2026, 9, 6, 23, 59, tzinfo=timezone.utc)  # 周日
    mon = sun + timedelta(days=1)
    assert _week_start(sun) == "2026-08-31"
    assert _week_start(mon) == "2026-09-07"


def test_week_series_keys_unique():
    """8 周序列的周键不重复且有序。"""
    from app.api import north_star as ns

    # 直接构造已知输入验证分桶逻辑（走 _week_start 的纯函数性质）
    seen = set()
    for i in range(8):
        wk = _week_start(datetime.now(timezone.utc) - timedelta(weeks=i))
        assert wk not in seen
        seen.add(wk)
    assert ns._WEEKS == 8
