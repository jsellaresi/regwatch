import argparse
import logging

from config import get_langfuse
from cache_invalidation import invalidate_analysis_cache

logger = logging.getLogger(__name__)


def promote_prompt(from_label: str, to_label: str):
    langfuse = get_langfuse()
    prompt = langfuse.get_prompt("compliance-analyzer", label=from_label)
    langfuse.create_prompt(
        name="compliance-analyzer",
        prompt=prompt.prompt,
        labels=[to_label],
        config=prompt.config,
    )
    logger.info("Prompt v%s promovido de '%s' a '%s'", prompt.version, from_label, to_label)

    # ADR-0006: only "production" is what analyze_compliance actually reads —
    # promoting to any other label doesn't change live analysis behavior, so
    # there's nothing stale to invalidate.
    if to_label == "production":
        invalidate_analysis_cache(reason=f"prompt v{prompt.version} promoted to production")


def main():
    import config

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config.validate_required()
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_label")
    parser.add_argument("--to", dest="to_label")
    args = parser.parse_args()
    promote_prompt(args.from_label, args.to_label)


if __name__ == "__main__":
    main()
