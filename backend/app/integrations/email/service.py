"""Email integration service placeholder"""

from .provider import send_email


def send_transactional_email(to, subject, template_name, context):
    send_email(to, subject, template_name)
