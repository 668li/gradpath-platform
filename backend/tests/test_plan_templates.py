"""规划模板 API 测试。"""


def test_list_templates(client, auth_headers):
    """测试列出模板。"""
    res = client.get("/api/plan-templates", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    # 验证模板结构
    t = data[0]
    assert "id" in t
    assert "name" in t
    assert "milestones" in t
    assert "goal_text" in t


def test_get_template(client, auth_headers):
    """测试获取单个模板。"""
    res = client.get("/api/plan-templates/backend_dev", headers=auth_headers)
    assert res.status_code == 200
    t = res.json()
    assert t["id"] == "backend_dev"
    assert len(t["milestones"]) >= 5


def test_get_template_not_found(client, auth_headers):
    """测试不存在的模板。"""
    res = client.get("/api/plan-templates/nonexistent", headers=auth_headers)
    assert res.status_code == 404
