"""Business logic.

A service exists when there are rules to enforce beyond CRUD: uniqueness, state
transitions, side effects like sending an email. It receives a `Session`, builds
the repositories it needs, and raises domain exceptions from `app/exceptions.py`.

It never sees an HTTP object and never writes SQL. That is what lets the rules
be tested without a client and reused from a script or a CLI.
"""
