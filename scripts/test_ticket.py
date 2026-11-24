from third_agent.database.queries import create_ticket

print("Known customer:", create_ticket("ali@example.com", "Damaged mouse", "The mouse arrived broken."))
print("Unknown customer:", create_ticket("nobody@example.com", "Test", "Test"))