from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

# Common disposable/burner email providers. Not exhaustive - this is a cheap
# deterrent against the trivial "spin up 10 accounts in 2 minutes" case, not
# a guarantee. New domains show up constantly; extend this list as needed.
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.info", "10minutemail.com",
    "tempmail.com", "temp-mail.org", "throwawaymail.com", "yopmail.com",
    "getnada.com", "trashmail.com", "fakeinbox.com", "sharklasers.com",
    "maildrop.cc", "dispostable.com", "mintemail.com", "mohmal.com",
}


def is_disposable_email(email):
    domain = email.rsplit("@", 1)[-1].lower().strip()
    return domain in DISPOSABLE_EMAIL_DOMAINS


def send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email/{uid}/{token}"

    send_mail(
        subject="Verify your Trust Gambit account",
        message=(
            f"Welcome to The Trust Gambit!\n\n"
            f"Click the link below to verify your email and activate your account:\n"
            f"{link}\n\n"
            f"If you didn't request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def resolve_verification_token(uidb64, token):
    """Returns the User if (uid, token) is valid and not expired, else None."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None

    if default_token_generator.check_token(user, token):
        return user
    return None
