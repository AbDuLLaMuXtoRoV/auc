from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_item(client: TestClient, seller_token: str) -> dict:
    response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Circular saw",
            "condition": "used",
            "starting_price": "75.00",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_conversation_send_reply_and_mark_read(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    buyer_token = _register_and_login(client, "buyer@example.com")
    item = _create_item(client, seller_token)

    conversation_response = client.post(
        "/api/v1/messages/conversations",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"item_id": item["id"]},
    )
    assert conversation_response.status_code == 201
    conversation = conversation_response.json()
    assert conversation["item_id"] == item["id"]
    assert conversation["seller_id"] == item["seller_id"]

    buyer_message_response = client.post(
        f"/api/v1/messages/conversations/{conversation['id']}/messages",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"body": "Is this still available?"},
    )
    assert buyer_message_response.status_code == 201
    buyer_message = buyer_message_response.json()
    assert buyer_message["is_read"] is False

    seller_reply_response = client.post(
        f"/api/v1/messages/conversations/{conversation['id']}/messages",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"body": "Yes, it is."},
    )
    assert seller_reply_response.status_code == 201

    detail_response = client.get(
        f"/api/v1/messages/conversations/{conversation['id']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["messages"]) == 2

    list_response = client.get(
        "/api/v1/messages/conversations",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert list_response.status_code == 200
    assert [entry["id"] for entry in list_response.json()] == [conversation["id"]]

    read_response = client.patch(
        f"/api/v1/messages/messages/{buyer_message['id']}/read",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True


def test_only_participants_can_view_conversation(client: TestClient) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    buyer_token = _register_and_login(client, "buyer@example.com")
    stranger_token = _register_and_login(client, "stranger@example.com")
    item = _create_item(client, seller_token)

    conversation_response = client.post(
        "/api/v1/messages/conversations",
        headers={"Authorization": f"Bearer {buyer_token}"},
        json={"item_id": item["id"]},
    )
    assert conversation_response.status_code == 201
    conversation_id = conversation_response.json()["id"]

    forbidden_detail = client.get(
        f"/api/v1/messages/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert forbidden_detail.status_code == 403

    forbidden_send = client.post(
        f"/api/v1/messages/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {stranger_token}"},
        json={"body": "Hello?"},
    )
    assert forbidden_send.status_code == 403
