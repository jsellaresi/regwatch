import config

# Unlike tests/ (pure unit tests, no live infra needed), evals/ genuinely calls
# the real LLM and fetches prompts from Langfuse, so real credentials are a
# hard requirement here. Fail fast with one clear message instead of letting
# a random downstream call surface a confusing error mid-run.
config.validate_required()
