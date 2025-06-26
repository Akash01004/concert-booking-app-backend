from rest_framework import serializers
from api.models import Concert, Ticket
from django.db.models import Sum
from django.contrib.auth import get_user_model

class ConcertSerializer(serializers.ModelSerializer):
    user_booked_tickets = serializers.SerializerMethodField()
    remaining_tickets = serializers.SerializerMethodField()

    class Meta:
        model = Concert
        fields = [
            'id', 'name', 'venue', 'ticket_price', 'available_tickets',
            'date_time', 'image', 'user_booked_tickets', 'remaining_tickets'
        ] # Ensure it includes the 2 computed fields

    def get_user_booked_tickets(self, concert):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            booked = Ticket.objects.filter(user=request.user, concert=concert).aggregate(total=Sum('quantity'))
            return booked['total'] or 0
        return 0

    def get_remaining_tickets(self, concert):
        booked = Ticket.objects.filter(concert=concert).aggregate(total=Sum('quantity'))['total'] or 0
        return concert.available_tickets - booked


class TicketBookingSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()



class TicketSerializer(serializers.ModelSerializer):
    concert = ConcertSerializer()

    class Meta:
        model = Ticket
        fields = ['id', 'concert', 'quantity']

User = get_user_model()

class UserBookingSummarySerializer(serializers.Serializer):
    username = serializers.CharField()
    bookings = serializers.ListField(
        child=serializers.DictField()
    )        