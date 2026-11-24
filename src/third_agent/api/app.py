import os
import secrets
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from third_agent.auth import create_token, hash_password, read_token, verify_password
from third_agent.database.queries import (
    add_approval_request,
    decide_approval,
    get_password_hash,
    list_pending_approvals,
)
from third_agent.graph.agent_graph import (
    PENDING_TEXT,
    get_pending_request,
    resume_agent,
    run_agent,
)

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI(title="Third Agent")

# Used when the email does not exist, so the response time looks the same
DUMMY_HASH = hash_password("dummy-password")


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatRequest(BaseModel):
    """What the client sends. FastAPI rejects anything that does not match."""

    question: str = Field(min_length=1, max_length=1000)
    # Send the same thread_id again to continue a conversation
    thread_id: str | None = Field(
        default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


class ChatResponse(BaseModel):
    """What we send back."""

    answer: str
    thread_id: str
    waiting_for_approval: bool


class Decision(BaseModel):
    approved: bool


# Tells FastAPI (and the /docs page) that we use "Bearer" tokens
bearer_scheme = HTTPBearer(auto_error=False)

def current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Read the token from 'Authorization: Bearer <token>' and return the email."""
    email = read_token(credentials.credentials) if credentials else None
    if email is None:
        raise HTTPException(status_code=401, detail="Please log in")
    return email


def require_reviewer(x_reviewer_key: str = Header(default="")) -> None:
    """Allow only people who know the reviewer key."""
    expected = os.getenv("REVIEWER_API_KEY", "")

    # No key configured means nobody gets in (safe by default)
    if not expected or not secrets.compare_digest(
        x_reviewer_key.encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid reviewer key")


@app.get("/health")
def health() -> dict:
    """A simple check that the service is alive."""
    return {"status": "ok"}


@app.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    stored = get_password_hash(body.email)

    # Always check a hash, even for unknown emails, so timing does not reveal them
    password_ok = verify_password(body.password, stored or DUMMY_HASH)

    if stored is None or not password_ok:
        # Same message for "no such email" and "wrong password"
        raise HTTPException(status_code=401, detail="Wrong email or password")

    return TokenResponse(access_token=create_token(body.email))


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, email: str = Depends(current_customer)) -> ChatResponse:
    # The conversation id the client sees (and sends back)
    public_id = body.thread_id or "chat-" + uuid.uuid4().hex
    # The id we really use: it includes the owner, taken from the signed token
    thread_id = f"{email}::{public_id}"

    # If this conversation is already waiting for a human, do not run the agent again
    if get_pending_request(thread_id) is not None:
        return ChatResponse(
            answer=PENDING_TEXT, thread_id=public_id, waiting_for_approval=True
        )

    answer = run_agent(body.question, thread_id, email)

    # If the agent paused, put the request in the review queue
    pending = get_pending_request(thread_id)
    if pending is not None:
        add_approval_request(thread_id, email, pending)

    return ChatResponse(
        answer=answer, thread_id=public_id, waiting_for_approval=pending is not None
    )


@app.get("/reviews", dependencies=[Depends(require_reviewer)])
def pending_reviews() -> list[dict]:
    """The reviewer sees every request that waits for a decision."""
    return list_pending_approvals()


@app.post("/reviews/{request_id}/decision", dependencies=[Depends(require_reviewer)])
def decide(request_id: int, body: Decision) -> dict:
    """The reviewer approves or rejects. Then the paused conversation continues."""
    thread_id = decide_approval(request_id, body.approved)
    if thread_id is None:
        raise HTTPException(
            status_code=404, detail="Request not found or already decided"
        )

    answer = resume_agent(thread_id, body.approved)
    return {"thread_id": thread_id, "approved": body.approved, "agent_answer": answer}