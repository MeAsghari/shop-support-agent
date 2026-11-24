from eval_cases import CASES

from third_agent.graph.support_graph import classify_node
from third_agent.rag.retrieval import search


def run() -> None:
    intent_ok = 0
    retrieval_ok = 0
    retrieval_total = 0

    for case in CASES:
        question = case["question"]

        # Test 1: did the classifier pick the right intent?
        predicted = classify_node({"question": question})["intent"]
        intent_pass = predicted == case["intent"]
        intent_ok += intent_pass

        line = f"{'PASS' if intent_pass else 'FAIL'} intent={predicted:<7} | {question}"

        # Test 2: for docs questions, is the right chunk in the top 3?
        if case["keyword"]:
            retrieval_total += 1
            chunks = search(question, k=3, max_distance=1.0)
            found = any(case["keyword"] in chunk["content"] for chunk in chunks)
            retrieval_ok += found
            line += f"  | retrieval: {'PASS' if found else 'FAIL'}"

        print(line)

    print(f"\nIntent accuracy: {intent_ok}/{len(CASES)}")
    print(f"Retrieval hit rate (top 3): {retrieval_ok}/{retrieval_total}")


if __name__ == "__main__":
    run()