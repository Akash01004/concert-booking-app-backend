from rest_framework import serializers
from .models import CustomUser, Concert, Ticket
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user

class ConcertSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Concert
        fields = '__all__'
class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        
class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['concert', 'quantity']  

    def validate(self, data):
        user = self.context['request'].user
        concert = data['concert']
        quantity = data['quantity']

        if quantity < 1:
            raise serializers.ValidationError("You must book at least 1 ticket.")

        if quantity > 3:
            raise serializers.ValidationError("Cannot book more than 3 tickets per concert.")

        existing = Ticket.objects.filter(user=user, concert=concert).first()
        if existing and existing.quantity + quantity > 3:
            raise serializers.ValidationError("Maximum 3 tickets allowed per concert.")

        if quantity > concert.available_tickets:
            raise serializers.ValidationError("Not enough tickets available.")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        concert = validated_data['concert']
        quantity = validated_data['quantity']

        # Update available tickets
        concert.available_tickets -= quantity
        concert.save()

        # Calculate total price
        total_price = concert.ticket_price * quantity

        ticket = Ticket.objects.create(
            user=user,
            concert=concert,
            quantity=quantity,
            noofseat=quantity,  
            totalprice=total_price,
        )
        return ticket


class TicketBookingSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)