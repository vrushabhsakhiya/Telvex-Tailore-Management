import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Force DEBUG=True to get the traceback
os.environ["DEBUG"] = "True"
import config.settings
config.settings.DEBUG = True

django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()
client = Client(raise_request_exception=True)

user = User.objects.first()
if user:
    client.force_login(user)
    try:
        response = client.get('/dashboard/')
        print('SUCCESS:', response.status_code)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('ERROR:', e)
else:
    print('No user')
