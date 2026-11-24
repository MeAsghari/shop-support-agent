from pathlib import Path


def load_chunks(folder: str) -> list[dict]:
    """Read every .md file in a folder and split it into paragraph chunks."""
    chunks = []

    for file in sorted(Path(folder).glob("*.md")):
        text = file.read_text(encoding="utf-8")

        # A blank line separates paragraphs, so we split on it
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:  # skip empty pieces
                # "source" is the file name without .md, like "return_policy"
                chunks.append({"source": file.stem, "content": paragraph})

    return chunks


if __name__ == "__main__":
    # Quick manual test
    for chunk in load_chunks("docs/knowledge"):
        print(chunk["source"], "->", chunk["content"][:40])