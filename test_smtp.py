import os
import django
from django.core.mail import send_mail
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    print(f"SMTP Host: {settings.EMAIL_HOST}")
    print(f"SMTP User: {settings.EMAIL_HOST_USER}")
    print(f"Default From: {settings.DEFAULT_FROM_EMAIL}")
    
    send_mail(
        'Telvex SMTP Test 2',
        'Testing from DEFAULT_FROM_EMAIL',
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
    print("\nSUCCESS: Email sent successfully!")
except Exception as e:
    print(f"\nFAILURE: Error sending email: {e}")
