# gitscout-demo-sandbox

A deliberately small repo used to demo Developer Mission Control. `slugify` has a known bug
(see `ISSUE.md`); the assistant triages it, patches it in a throwaway sandbox, runs the tests and
opens a draft pull request, pausing for approval before every step that writes.

Run the tests: `pip install -r requirements-dev.txt && pytest -q` (two fail until the bug is fixed).
