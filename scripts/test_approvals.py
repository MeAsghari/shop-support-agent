from third_agent.database.queries import (
    add_approval_request,
    decide_approval,
    list_pending_approvals,
)

request_id = add_approval_request(
    "test-thread", "ali@example.com", {"requests": [{"tool": "create_ticket"}]}
)
print("Added:", request_id)
print("Same thread again:", add_approval_request("test-thread", "ali@example.com", {}))

print("Pending:", [row["id"] for row in list_pending_approvals()])

print("First decision:", decide_approval(request_id, True))
print("Second decision:", decide_approval(request_id, False))

print("Pending now:", [row["id"] for row in list_pending_approvals()])