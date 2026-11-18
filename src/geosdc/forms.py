from django.contrib.admin.forms import AdminAuthenticationForm
from geonode.people.forms.recaptcha import ReCaptchaField


class AdminReCaptchaAuthenticationForm(AdminAuthenticationForm):
    """Login do admin do Django com reCAPTCHA (ligado em urls.py quando RECAPTCHA_ENABLED=True)."""

    captcha = ReCaptchaField(label=False)
