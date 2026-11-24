import pytest
from fastapi.testclient import TestClient

import third_agent.api.app as api_module


@pytest.fixture(autouse=True)
def test_secrets(monkeypatch):
    # Fixed secrets for every test, so tests never depend on the real .env
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-" + "x" * 32)
    monkeypatch.setenv("REVIEWER_API_KEY", "test-reviewer-key")


class FakeBackend:
    """Fake versions of the agent, the database, and the review queue."""

    def __init__(self):
        self.agent_calls = []  # every (question, thread_id, email) the agent received
        self.resume_calls = []  # every (thread_id, approved) used to resume
        self.queue = []  # requests that were added to the review queue
        self.paused = {}  # thread_id -> payload, for conversations waiting for a human
        self.pending_rows = []  # what the reviewer list returns
        self.decisions = {}  # request_id -> thread_id, still undecided
        self.hashes = {}  # email -> stored password hash
        self.pause_next_call = False  # if True, the next agent call "pauses"

    def run_agent(self, question, thread_id, email=""):
        self.agent_calls.append((question, thread_id, email))
        if self.pause_next_call:
            self.paused[thread_id] = {"requests": [{"tool": "create_ticket"}]}
            return "waiting"
        return f"answer for {email}"

    def get_pending_request(self, thread_id):
        return self.paused.get(thread_id)

    def add_approval_request(self, thread_id, email, payload):
        self.queue.append((thread_id, email, payload))
        return len(self.queue)

    def resume_agent(self, thread_id, approved):
        self.resume_calls.append((thread_id, approved))
        return "resumed"

    def decide_approval(self, request_id, approved):
        # pop() removes the item, so a second decision for the same id gets None
        # (this copies what our real UPDATE does)
        return self.decisions.pop(request_id, None)

    def list_pending_approvals(self):
        return self.pending_rows

    def get_password_hash(self, email):
        return self.hashes.get(email)


@pytest.fixture
def backend(monkeypatch):
    fake = FakeBackend()
    # Replace the real functions inside the API module with the fake ones
    for name in [
        "run_agent",
        "get_pending_request",
        "add_approval_request",
        "resume_agent",
        "decide_approval",
        "list_pending_approvals",
        "get_password_hash",
    ]:
        monkeypatch.setattr(api_module, name, getattr(fake, name))
    return fake


@pytest.fixture
def client(backend):
    # Asking for "backend" first guarantees the fakes are in place
    return TestClient(api_module.app)