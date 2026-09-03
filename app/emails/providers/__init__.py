"""Email adapters. One module per delivery mechanism.

Each one implements `app.emails.base.EmailSender` and knows nothing about the
rest of the application. Adding a provider means adding a module here and a
value to `EmailProvider` in `app/config.py`.
"""
