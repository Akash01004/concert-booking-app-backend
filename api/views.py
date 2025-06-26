
from rest_framework import viewsets, generics, permissions
from .serializers import ConcertSerializer, BookingSerializer, RegisterSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Concert, Ticket, CustomUser
from .forms import TicketBookingForm
from django.core.mail import send_mail
from django.conf import settings
import qrcode
import io
from django.http import JsonResponse
import base64
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.db.models import Prefetch

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_admin

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer

class ConcertViewSet(viewsets.ModelViewSet):
    queryset = Concert.objects.all()
    serializer_class = ConcertSerializer
    permission_classes = [IsAdminOrReadOnly]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user)

def perform_create(self, serializer):
        serializer.save(user=self.request.user)

#home page
def home(request):
         
         return render(request, 'home.html')

#register
def register_page(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login_page')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

#login
def login_page(request):
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_dashboard') 
            else:
                return redirect('user_dashboard') 
        else:
            return render(request, 'login.html', {
                'error': 'Invalid username or password.'
            })

    return render(request, 'login.html')

#logout
def logout_view(request):
    logout(request)
    return redirect('/')

#list
def concert_list(request):
    concerts = Concert.objects.all()
    print(concerts)
    return render(request, 'concerts_list.html', {'concerts': concerts})

#concert detail
def concert_detail(request, pk):
    concert = get_object_or_404(Concert, pk=pk)

    data = {
        'id': concert.id,
        'name': concert.name,
        'date_time': concert.date_time,
        'venue': concert.venue,
        'ticket_price': concert.ticket_price,
        'available_tickets': concert.available_tickets,
        'image': concert.image.url if concert.image else None,
    }

    return JsonResponse(data)

#concert create
@login_required
def concert_create(request):
    if not request.user.is_superuser: 
        return redirect('/login')

    if request.method == 'POST':
        name = request.POST.get('name')
        date_time = request.POST.get('date_time')
        venue = request.POST.get('venue')
        ticket_price = request.POST.get('ticket_price')
        available_tickets = request.POST.get('available_tickets')
        image = request.FILES.get('image') 
        
        Concert.objects.create(
            name=name,
            date_time=date_time,
            venue=venue,
            ticket_price=ticket_price,
            available_tickets=available_tickets,
            image=image

            
        )
        return redirect('/concerts_list')

    return render(request, 'concert_create.html')

#concert edit
def concert_update(request, pk):
    if not request.user.is_superuser:
        return redirect('/login')
    concert = get_object_or_404(Concert, pk=pk)
    if request.method == 'POST':
        concert.name = request.POST.get('name')
        concert.date_time = request.POST.get('date_time')
        concert.venue = request.POST.get('venue')
        concert.ticket_price = request.POST.get('ticket_price')
        concert.available_tickets = request.POST.get('available_tickets')
        image = request.FILES.get('image') 
        if image:
            concert.image = image
        concert.save()
        return redirect('concert_list')
    return render(request, 'concert_update.html',{'concert':concert} )


#concert delete
def concert_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('/login')

    concert = get_object_or_404(Concert, pk=pk)

    if request.method == 'POST':
        concert.delete()
        return redirect('/admin_dashboard')

    return render(request, 'concert_delete.html', {'concert': concert})


#admin dashboard
@staff_member_required
def admin_dashboard(request):
    concerts = Concert.objects.all().order_by('-date_time')

    users = CustomUser.objects.prefetch_related(
        Prefetch('ticket_set', queryset=Ticket.objects.select_related('concert'))
    )

    return render(request, 'admin_dashboard.html', {
        'concerts': concerts,
        'users': users,
    })

#user dashboard 
@login_required
def user_dashboard(request):
    user = request.user
    concerts = Concert.objects.all()

    for concert in concerts:
        concert.booked_count = concert.ticket_set.aggregate(total=Sum('quantity'))['total'] or 0
        concert.remaining_tickets = concert.available_tickets - concert.booked_count
        concert.user_booked_tickets = concert.ticket_set.filter(user=user).aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'user_dashboard.html', {
        'concerts': concerts
    })

#user list view
@staff_member_required
def user_list_view(request):
    users = CustomUser.objects.filter(is_superuser=False)

    grouped_users = []

    for user in users:
        bookings = (
            Ticket.objects
            .filter(user=user)
            .values('concert__name')
            .annotate(total_tickets=Sum('quantity'))
        )

        grouped_users.append({
            'username': user.username,
            'bookings': bookings
        })

    return render(request, 'user_list.html', {'grouped_users': grouped_users})

#ticket booking
@login_required
def bookticket(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    user = request.user

    existing_ticket = Ticket.objects.filter(user=user, concert=concert).first()
    already_booked = existing_ticket.quantity if existing_ticket else 0

    max_tickets = 3
    remaining_slots = max(0, max_tickets - already_booked)

    if request.method == 'POST':
        form = TicketBookingForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']

            with transaction.atomic():
                concert.refresh_from_db()
                available_capacity = concert.available_tickets

                if quantity > remaining_slots:
                    messages.error(request, f"You can only book {remaining_slots} more ticket(s).")
                elif quantity > available_capacity:
                    messages.error(request, f"Only {available_capacity} ticket(s) available.")
                else:
                    if existing_ticket:
                        existing_ticket.quantity += quantity
                        existing_ticket.total_price = Decimal(existing_ticket.quantity) * concert.ticket_price
                        existing_ticket.save()
                        total_price = existing_ticket.total_price
                    else:
                        total_price = Decimal(quantity) * concert.ticket_price
                        Ticket.objects.create(
                            user=user,
                            concert=concert,
                            quantity=quantity,
                            total_price=total_price
                        )

                    concert.available_tickets -= quantity
                    concert.save()

                    request.session['booking_total_price'] = float(total_price)
                    request.session['booking_quantity'] = quantity

                    send_booking_email(user, concert, quantity, total_price)

                    return redirect('booking_confirmation', concert_id=concert.id)
    else:
        form = TicketBookingForm()

    return render(request, 'book_ticket.html', {
        'concert': concert,
        'form': form,
        'already_booked': already_booked,
        'remaining_slots': remaining_slots,
        'available_capacity': concert.available_tickets,
    })

               
#cancel ticket
@login_required
def ticketcancel(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    concert = ticket.concert
    quantity = 1  
    refund_amount = quantity * concert.ticket_price

    if request.method == 'POST':
        concert.available_tickets += quantity
        concert.save()

        ticket.delete()

        send_cancellation_email(request.user, concert, quantity, refund_amount)

        messages.success(request, "Your booking has been cancelled.")
        return redirect('my_bookings')

    return render(request, 'cancel_ticket_confirm.html', {'ticket': ticket})


#book confirmation
def booking_confirmation(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    total_price = request.session.pop('booking_total_price', None)
    quantity = request.session.pop('booking_quantity', None)

    return render(request, 'booking_confirmation.html', {
        'concert': concert,
        'total_price': total_price,
        'quantity': quantity,
    })

#booking view
def booking_detail(request, ticket_id):
    booking = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    concert = booking.concert

    quantity = booking.quantity or 0
    price = concert.ticket_price or 0
    total_price = quantity * price
    
    qr_data = f"""
    Ticket ID: {booking.id}
    User: {booking.user.username}
    Concert: {concert.name}
    Quantity: {quantity}
    Total Price: ₹{total_price}
    'ticket_id': ticket_id 
    """

    
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render(request, 'booking_detail.html', {
        'booking': booking,
        'concert': concert,
        'total_price': total_price,
        'qr_code': qr_base64
    })


#my bookings
@login_required
def my_bookings(request):
    tickets = Ticket.objects.filter(user=request.user).select_related('concert')
   
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    if search_query:
        tickets = tickets.filter(
            Q(concert__name__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    return render(request, 'my_bookings.html', {
        'bookings': tickets
    })



#booking summary
@login_required
def booking_summary(request):
    tickets = Ticket.objects.filter(user=request.user).select_related('concert')
    
    total_price = sum(ticket.quantity * ticket.concert.ticket_price for ticket in tickets)
    

    return render(request, 'booking_summary.html', {
        'tickets': tickets,
        'total_price': total_price
    })

#pdf
@login_required
def ticket_pdf_view(request, ticket_id):
    booking = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    concert = booking.concert

    quantity = booking.quantity or 0
    price = concert.ticket_price or 0
    total_price = quantity * price

    qr_data = f"""
    Ticket ID: {booking.id}
    User: {booking.user.username}
    Concert: {concert.name}
    Quantity: {quantity}
    Total Price: ₹{total_price}
    """
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'booking': booking,
        'concert': concert,
        'total_price': total_price,
        'qr_code': qr_base64
    }

    return render_to_pdf('pdf/ticket.html', context)

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), dest=result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse("Error generating PDF", status=500)

#sent book ticket mail
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

#sent cancel ticket mail
def send_cancellation_email(user, concert, quantity, refund_amount):
    subject = '❌ Ticket Cancellation Confirmation'
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    context = {
        'user': user,
        'concert': concert,
        'quantity': quantity,
        'refund_amount': refund_amount,
    }

    text_content = render_to_string('email/cancellation_confirmation.txt', context)
    html_content = render_to_string('email/cancellation_confirmation.html', context)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    msg.send()







