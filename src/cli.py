"""Talk to Vaani in the terminal (text only). Best way to test the brain.

Run:  py -m src.cli
Type 'quit' to stop.
"""
from .pipeline import Vaani


def main():
    vaani = Vaani()
    session = "cli"
    print(f"Vaani ready (retriever: {vaani.kind}). Type a health question. 'quit' to stop.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("quit", "exit"):
            vaani.end(session)   # forget the conversation, like closing the app
            break
        result = vaani.ask(text, session_id=session)
        print(f"\nVaani [{result['status']}, trust={result['trust']}, score={result['score']}]")
        print(result["answer"])
        if result["sources"]:
            print("Source:", "; ".join(result["sources"]))


if __name__ == "__main__":
    main()
