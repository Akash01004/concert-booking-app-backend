from django.shortcuts import render

# Create your views here.
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


from rest_framework import status
from rest_framework import permissions
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm 


from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from .serializers import ConcertSerializer
from api.models import Concert
from api.models import Ticket
from .serializers import TicketBookingSerializer
from .serializers import TicketSerializer

from django.db.models import Q
import qrcode
import io
import base64
from rest_framework.views import APIView
from django.http import HttpResponse, Http404
from django.template.loader import get_template
from xhtml2pdf import pisa
from api.models import Ticket
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from .serializers import UserBookingSummarySerializer
from django.db.models import Sum
from rest_framework.permissions import IsAdminUser
from concert_booking.utils.email_utils import send_booking_email
from .serializers import TicketBookingSerializer




@csrf_exempt
@api_view(["GET"])
@permission_classes((AllowAny,))
def simpleapi(request):
    return Response({'text': 'Hello world, This is your first and second api call'},status=HTTP_200_OK)

#register
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    form = CustomUserCreationForm(data=request.data)
    if form.is_valid():
        form.save()
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
    else:
        print("Form errors:", form.errors)
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

#login
@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    
    if username is None or password is None:
        return Response({'error': 'Please provide both username and password'}, status=HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)

    if not user:
        return Response({'error': 'Invalid Credentials'}, status=HTTP_404_NOT_FOUND)

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'is_superuser': user.is_superuser
    }, status=HTTP_200_OK)

#user list
User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAdminUser])  
def user_list_api(request):
    users = User.objects.filter(is_superuser=False)
    data = []

    for user in users:
        bookings = (
            Ticket.objects
            .filter(user=user)
            .values('concert__name')
            .annotate(total_tickets=Sum('quantity'))
        )

        data.append({
            'username': user.username,
            'bookings': list(bookings)
        })

    serializer = UserBookingSummarySerializer(data, many=True)
    return Response(serializer.data)

# CREATE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking(request):
    data = request.data.copy()
    data['user'] = request.user.id
    serializer = ConcertSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Detail
@api_view(['GET'])
@permission_classes((AllowAny,))
def concert_detail(request, pk):
    concert = get_object_or_404(Concert, pk=pk)
    serializer = ConcertSerializer(concert)
    return Response(serializer.data)

# List
@api_view(['GET'])
@permission_classes((AllowAny,))
def concerts(request):
    concerts = Concert.objects.all()
    serializer = ConcertSerializer(concerts, many=True, context={'request': request})
    return Response(serializer.data)

# UPDATE
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_booking(request, pk):
    try:
        concert = Concert.objects.get(pk=pk)
    except Concert.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = ConcertSerializer(concert, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# DELETE
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_booking(request, pk):
    try:
        concert = Concert.objects.get(pk=pk)
    except Concert.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
    
    concert.delete()
    return Response({"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


# Book Ticket - CREATE
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_ticket(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    user = request.user

    existing_ticket = Ticket.objects.filter(user=user, concert=concert).first()
    already_booked = existing_ticket.quantity if existing_ticket else 0
    max_tickets = 3
    remaining_slots = max(0, max_tickets - already_booked)

    serializer = TicketBookingSerializer(data=request.data)
    if serializer.is_valid():
        quantity = serializer.validated_data['quantity']

        if quantity < 1:
            return Response({"error": "You must book at least 1 ticket."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity > remaining_slots:
            return Response(
                {"error": f"You can only book {remaining_slots} more ticket(s)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            concert.refresh_from_db()  # Lock row for concurrency safety
            available_capacity = concert.available_tickets

            if quantity > available_capacity:
                return Response(
                    {"error": f"Only {available_capacity} ticket(s) available."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if existing_ticket:
                    existing_ticket.quantity += quantity
                    existing_ticket.total_price = Decimal(existing_ticket.quantity) * concert.ticket_price
                    existing_ticket.save()
                    ticket = existing_ticket
                else:
                    total_price = Decimal(quantity) * concert.ticket_price
                    ticket = Ticket.objects.create(
                        user=user,
                        concert=concert,
                        quantity=quantity,
                        total_price=total_price
                    )

                # Update concert availability
                concert.available_tickets -= quantity
                concert.save()

                # Send booking confirmation email
                try:
                    send_booking_email(
                        user=user,
                        concert=concert,
                        quantity=ticket.quantity,
                        total_price=ticket.total_price
                    )
                except Exception as e:
                    # Log error but don't fail booking
                    print(f"Failed to send booking email: {e}")

                ticket_info = {
                    "id": ticket.id,
                    "quantity": ticket.quantity,
                    "total_price": float(ticket.total_price)
                }

                return Response({
                    "message": "Tickets booked successfully.",
                    "ticket": ticket_info,
                    "concert_id": concert.id,
                    "user": user.username,
                    "remaining_slots": max(0, max_tickets - (already_booked + quantity)),
                    "available_capacity": concert.available_tickets
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": "Failed to book tickets. Try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#book detail
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_detail(request, ticket_id):
    booking = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    concert = booking.concert

    quantity = booking.quantity or 0
    price = concert.ticket_price or 0
    total_price = quantity * price

    # Status handling based on 'canceled' field or similar
    ticket_status = "Canceled" if getattr(booking, 'canceled', False) else "Active"

    # QR Code data
    qr_data = f"""
    Ticket ID: {booking.id}
    User: {request.user.username}
    Concert: {concert.name}
    Quantity: {quantity}
    Total Price: ₹{total_price}
    """

    # Generate QR code image and encode as base64
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return Response({
    'ticket_id': booking.id,
    'concert': {
        'id': concert.id,
        'name': concert.name,
        'venue': concert.venue,
        'date_time': concert.date_time,
        'ticket_price': concert.ticket_price
    },
    'quantity': quantity,
    'total_price': total_price,
    'status': ticket_status,
    'qr_code_base64': qr_base64
}, status=status.HTTP_200_OK)


#my bookings
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    tickets = Ticket.objects.filter(user=request.user).select_related('concert')

    # Optional query params
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # Filter by concert name or ticket ID
    if search_query:
        tickets = tickets.filter(
            Q(concert__name__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    if status_filter:
        tickets = tickets.filter(status__iexact=status_filter)

    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

#summary
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_summary(request):
    tickets = Ticket.objects.filter(user=request.user).select_related('concert')
    total_price = sum(ticket.quantity * ticket.concert.ticket_price for ticket in tickets)
    serializer = TicketSerializer(tickets, many=True)

    return Response({
        'tickets': serializer.data,
        'total_price': total_price
    })

# Cancel Ticket - DELETE
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Update concert available tickets
    concert = ticket.concert
    concert.available_tickets += ticket.quantity  # Assuming quantity can be greater than 1
    concert.save()

    # Delete the ticket
    ticket.delete()

    return Response(
        {"message": "Your ticket has been successfully cancelled."},
        status=status.HTTP_204_NO_CONTENT
    )

#pdf 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_pdf_api(request, ticket_id):
    try:
        ticket = Ticket.objects.select_related('concert').get(id=ticket_id, user=request.user)
    except Ticket.DoesNotExist:
        raise Http404("Ticket not found.")

    concert = ticket.concert
    quantity = ticket.quantity or 0
    price = concert.ticket_price or 0
    total_price = quantity * price

    # Generate QR code data
    qr_data = f"""
    Ticket ID: {ticket.id}
    User: {request.user.username}
    Concert: {concert.name}
    Quantity: {quantity}
    Total Price: ₹{total_price}
    """
    qr = qrcode.make(qr_data)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Context for rendering the PDF
    context = {
        'booking': ticket,
        'concert': concert,
        'total_price': total_price,
        'qr_code': qr_base64
    }

    # Render template to PDF
    template = get_template('pdf/ticket.html')
    html = template.render(context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), dest=result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket_id}.pdf"'
        return response

    return Response({"error": "Error generating PDF"}, status=500)

#mailtarp for booking
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_booking_email_api(request, concert_id):
    user = request.user
    concert = get_object_or_404(Concert, id=concert_id)
    ticket = Ticket.objects.filter(user=user, concert=concert).first()

    if not ticket:
        return Response({"error": "No ticket found for this user and concert."}, status=status.HTTP_404_NOT_FOUND)

    try:
        send_booking_email(
            user=user,
            concert=concert,
            quantity=ticket.quantity,
            total_price=ticket.total_price
        )
        # Explicitly return JSON response with success message and status 200
        return Response({"message": "Booking email sent successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        # Log exception on server side for debugging
        import logging
        logging.error(f"Error sending booking email: {e}")

        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)