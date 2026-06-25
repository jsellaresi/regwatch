import argparse
from config import langfuse


def promote_prompt(from_label: str, to_label: str):
    prompt = langfuse.get_prompt("compliance-analyzer", label=from_label)
    langfuse.create_prompt(
        name="compliance-analyzer",
        prompt=prompt.prompt,
        labels=[to_label],
        config=prompt.config,
    )
    print(f"Prompt v{prompt.version} promovido de '{from_label}' a '{to_label}'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_label")
    parser.add_argument("--to", dest="to_label")
    args = parser.parse_args()
    promote_prompt(args.from_label, args.to_label)


if __name__ == "__main__":
    main()
