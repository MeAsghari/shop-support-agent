import uuid

from third_agent.graph.agent_graph import get_pending_request, resume_agent, run_agent

thread_id = "ticket-" + uuid.uuid4().hex[:8]

print("CUSTOMER SAYS: ماوسی که خریدم خراب بود، می‌خوام شکایت ثبت کنم")
print("AGENT:", run_agent("ماوسی که خریدم خراب بود، می‌خوام شکایت ثبت کنم", thread_id, "ali@example.com"))

pending = get_pending_request(thread_id)
print("\nWAITING FOR APPROVAL:", pending)

if pending:
    print("\n(Now check the database in another terminal. No new ticket should exist yet.)")
    answer = input("Approve? (y/n): ")
    print("AGENT:", resume_agent(thread_id, answer.strip().lower() == "y"))