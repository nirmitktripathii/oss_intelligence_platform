"""Check that Amazon Bedrock answers, without printing any credential.

Run from the backend directory with the key already in your shell's environment:

    PowerShell:  $env:AWS_BEARER_TOKEN_BEDROCK = "<your key>"
                 python scripts/check_bedrock.py

Forces the Bedrock provider (no silent fallback to Gemini) and prints only the provider label,
the reply and the error class, so the output is safe to paste into a chat or an issue.
"""

import asyncio
import os
import sys
import time

os.environ["LLM_PROVIDER"] = "bedrock"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.triage.llm_engine import LLMTriageEngine  # noqa: E402


async def main() -> int:
    chain = LLMTriageEngine.resolve_chain()
    if not chain:
        print("Bedrock is NOT enabled: set AWS_BEARER_TOKEN_BEDROCK (or BEDROCK_AWS_PROFILE) first.")
        return 2
    print("model:", chain[0][1])
    started = time.time()
    result = await LLMTriageEngine.query_llm_with_provenance(
        'Reply with exactly this JSON and nothing else: {"ok": true}', temperature=0.0
    )
    took = time.time() - started
    if result is None:
        print(f"FAILED after {took:.1f}s. See the warning line above for the error class "
              "(ValidationException 'Operation not allowed' = account quota still 0).")
        return 1
    text, provenance = result
    print(f"OK in {took:.1f}s via {provenance}")
    print("reply:", text.strip()[:200])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
