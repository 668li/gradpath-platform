def test_provider_registry_and_routing(client):
    response = client.get("/api/evidence-providers")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"university", "cutoff", "salary", "company", "recruitment", "civil_service", "employment"} <= names

    routed = client.post(
        "/api/evidence-providers/route",
        json={"hypothesis": "我的考研分数能达到目标院校复试线，而且毕业后薪资可以达到预期"},
    )
    assert routed.status_code == 200
    routed_names = [item["name"] for item in routed.json()["providers"]]
    assert routed_names[:2] == ["cutoff", "salary"]
