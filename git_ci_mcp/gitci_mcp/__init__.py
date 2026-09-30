"""Git/CI MCP server: fork-safe branch, patch, test, and draft-PR tools over one sandbox.

Lets an agent (Alexa+, Claude Code, the GitScout web client) turn a triaged issue into a
reviewed change: clone an allow-listed repo into a throwaway sandbox, branch, apply a patch,
run the project's tests, and open a DRAFT pull request. Streamable HTTP, like GitScout MCP.
"""

__version__ = "0.1.0"
