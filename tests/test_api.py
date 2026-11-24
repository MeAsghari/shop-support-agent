import pytest

import third_agent.api.app as api_module
from third_agent.auth import create_token, hash_password, read_token

REVIEWER = {"X-Reviewer-Key": "test-reviewer-key"}


def auth(email):
    """Headers of a logged-in customer."""
    return {"Authorization": f"Bearer {create_token(email)}"}


# ---------- basics ----------


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# ---------- login ----------


def test_login_gives_a_token_for_the_right_person(client, backend):
    backend.hashes["ali@example.com"] = hash_password("correct-password")
    response = client.post(
        "/login", json={"email": "ali@example.com", "password": "correct-password"}
    )
    assert response.status_code == 200
    assert read_token(response.json()["access_token"]) == "ali@example.com"


def test_wrong_password_and_unknown_email_look_the_same(client, backend):
    backend.hashes["ali@example.com"] = hash_password("correct-password")

    wrong = client.post(
        "/login", json={"email": "ali@example.com", "password": "wrong-password"}
    )
    unknown = client.post(
        "/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    # An attacker must not learn which emails exist
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


# ---------- chat: who are you? ----------


def test_chat_without_token_is_rejected(client, backend):
    response = client.post("/chat", json={"question": "سفارشم کجاست؟"})
    assert response.status_code == 401
    assert backend.agent_calls == []  # the agent was never called


def test_chat_with_fake_token_is_rejected(client, backend):
    response = client.post(
        "/chat",
        json={"question": "سفارشم کجاست؟"},
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert response.status_code == 401
    assert backend.agent_calls == []


def test_email_comes_from_the_token_not_from_a_header(client, backend):
    response = client.post(
        "/chat",
        json={"question": "سفارشم کجاست؟"},
        # Ali is logged in, but he writes Sara's email in an old-style header
        headers={**auth("ali@example.com"), "X-Customer-Email": "sara@example.com"},
    )
    assert response.status_code == 200
    _, _, email = backend.agent_calls[0]
    assert email == "ali@example.com"


# ---------- chat: conversations belong to their owner ----------


def test_same_thread_id_for_two_customers_stays_separate(client, backend):
    for email in ("ali@example.com", "sara@example.com"):
        response = client.post(
            "/chat",
            json={"question": "hello", "thread_id": "chat-1"},
            headers=auth(email),
        )
        # The client only ever sees the public id
        assert response.json()["thread_id"] == "chat-1"

    # But inside, each customer got a different conversation
    used_ids = [call[1] for call in backend.agent_calls]
    assert used_ids == ["ali@example.com::chat-1", "sara@example.com::chat-1"]


def test_new_conversation_gets_a_random_id(client, backend):
    response = client.post(
        "/chat", json={"question": "hello"}, headers=auth("ali@example.com")
    )
    assert response.json()["thread_id"].startswith("chat-")


# ---------- chat: input validation ----------


@pytest.mark.parametrize(
    "body",
    [
        {"question": ""},
        {"question": "x" * 1001},
        {"question": "hello", "thread_id": "a b/c"},
        {"question": "hello", "thread_id": "x" * 65},
    ],
)
def test_bad_input_is_rejected_before_reaching_the_agent(client, backend, body):
    response = client.post("/chat", json=body, headers=auth("ali@example.com"))
    assert response.status_code == 422
    assert backend.agent_calls == []


# ---------- human approval ----------


def test_paused_conversation_goes_to_the_review_queue(client, backend):
    backend.pause_next_call = True
    response = client.post(
        "/chat",
        json={"question": "complaint", "thread_id": "chat-9"},
        headers=auth("ali@example.com"),
    )

    assert response.json()["waiting_for_approval"] is True
    thread_id, email, _ = backend.queue[0]
    assert thread_id == "ali@example.com::chat-9"
    assert email == "ali@example.com"


def test_waiting_conversation_does_not_run_the_agent_again(client, backend):
    backend.paused["ali@example.com::chat-9"] = {"requests": []}

    response = client.post(
        "/chat",
        json={"question": "hello again", "thread_id": "chat-9"},
        headers=auth("ali@example.com"),
    )

    assert response.json()["answer"] == api_module.PENDING_TEXT
    assert backend.agent_calls == []


@pytest.mark.parametrize("headers", [{}, {"X-Reviewer-Key": "wrong-key"}])
def test_reviewer_endpoints_need_the_right_key(client, backend, headers):
    assert client.get("/reviews", headers=headers).status_code == 401
    response = client.post(
        "/reviews/1/decision", json={"approved": True}, headers=headers
    )
    assert response.status_code == 401
    assert backend.resume_calls == []


def test_customer_token_is_not_a_reviewer_key(client, backend):
    # A logged-in customer must not be able to approve their own request
    response = client.get("/reviews", headers=auth("ali@example.com"))
    assert response.status_code == 401


def test_reviewer_endpoints_are_closed_when_no_key_is_configured(
    client, backend, monkeypatch
):
    monkeypatch.delenv("REVIEWER_API_KEY")
    assert client.get("/reviews", headers={"X-Reviewer-Key": ""}).status_code == 401


def test_reviewer_sees_the_pending_list(client, backend):
    backend.pending_rows = [{"id": 1, "thread_id": "t", "payload": {}}]
    response = client.get("/reviews", headers=REVIEWER)
    assert response.status_code == 200
    assert response.json()[0]["id"] == 1


@pytest.mark.parametrize("approved", [True, False])
def test_decision_resumes_the_conversation(client, backend, approved):
    backend.decisions[5] = "ali@example.com::chat-9"

    response = client.post(
        "/reviews/5/decision", json={"approved": approved}, headers=REVIEWER
    )

    assert response.status_code == 200
    assert backend.resume_calls == [("ali@example.com::chat-9", approved)]


def test_a_request_can_only_be_decided_once(client, backend):
    backend.decisions[5] = "ali@example.com::chat-9"

    first = client.post("/reviews/5/decision", json={"approved": True}, headers=REVIEWER)
    second = client.post("/reviews/5/decision", json={"approved": True}, headers=REVIEWER)

    assert first.status_code == 200
    assert second.status_code == 404
    assert len(backend.resume_calls) == 1  # the ticket can never be created twice