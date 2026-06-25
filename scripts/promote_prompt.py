import argparse
import logging

from config import langfuse

logger = logging.getLogger(__name__)


def promote_prompt(from_label: str, to_label: str):
    prompt = langfuse.get_prompt("compliance-analyzer", label=from_label)
    langfuse.create_prompt(
        name="compliance-analyzer",
        prompt=prompt.prompt,
        labels=[to_label],
        config=prompt.config,
    )
    logger.info("Prompt v%s promovido de '%s' a '%s'", prompt.version, from_label, to_label)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_label")
    parser.add_argument("--to", dest="to_label")
    args = parser.parse_args()
    promote_prompt(args.from_label, args.to_label)


if __name__ == "__main__":
    main()
