from django.urls import path
from . import views
from .views import ticket_pdf_api
from .views import user_list_api
from .views import send_booking_email_api

urlpatterns = [
    path('simpleapi/', views.simpleapi, name='simpleapi'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('users/', views.user_list_api, name='user_list_api'),
    
    #Concert CRED
    path('concerts/create/', views.create_booking, name='create_booking'),
    path('concerts/', views.concerts, name='concerts_list'),
    path('concerts/<int:pk>/', views.concert_detail, name='concert_detail'),
    path('concerts/<int:pk>/update/', views.update_booking, name='update_booking'),
    path('concerts/<int:pk>/delete/', views.delete_booking, name='delete_booking'),

    #Ticket CRED
    path('concerts/<int:concert_id>/book/', views.book_ticket, name='book_ticket'),
    path('tickets/<int:ticket_id>/', views.booking_detail, name='book_detail'),
    path('tickets/<int:ticket_id>/cancel/', views.cancel_ticket, name='cancel_ticket'),
    path('tickets/', views.my_bookings, name='my-bookings-api'),
    path('booking-summary/', views.booking_summary, name='booking-summary'),
    path('tickets/<int:ticket_id>/pdf/', views.ticket_pdf_api, name='ticket-pdf-api'),

    #mailtrap
    path('api/send-booking-email/<int:concert_id>/', send_booking_email_api, name='send_booking_email_api'),


]