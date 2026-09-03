"""ASGI middleware.

Cross-cutting behaviour that has to happen on every request, in the order they
are added in `app.main.create_app`. Anything that belongs to one route is a
dependency, not a middleware.
"""
