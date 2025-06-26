from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_booking_email(user, concert, quantity, total_price):
    subject = 'Booking Confirmation - Concert Ticket'
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    context = {
        'user': user,
        'concert': concert,
        'quantity': quantity,
        'total_price': total_price,
    }

    text_content = render_to_string('email/booking_confirmation.txt', context)
    html_content = render_to_string('email/booking_confirmation.html', context)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
