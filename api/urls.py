from . import views
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import user_list_view
from .views import ticket_pdf_view 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    ConcertViewSet, BookingViewSet, RegisterView,
    login_page, logout_view, register_page, home,
    concert_list, concert_create,
    concert_update, concert_delete, concert_detail,booking_summary
)

router = DefaultRouter()
router.register('concerts/api', ConcertViewSet, basename='concert')
router.register('bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login_page'),            
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_page, name='register_page'), 
    path('admin_dashboard/users/', user_list_view, name='user_list'),
        
    
    #CRED
    path('concerts_list/', views.concert_list, name='concert_list'),
    path('concerts/create/', views.concert_create, name='concert_create'),
    path('concerts/update/<int:pk>/',views.concert_update, name='concert_update'),
    path('concerts/delete/<int:pk>/',views.concert_delete, name='concert_delete'),
    path('concerts/<int:pk>/', views.concert_detail, name='concert_detail'),

    path('api/register/', RegisterView.as_view()),
    path('api/', include(router.urls)),

    #Dashboard
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user_dashboard/', views.user_dashboard, name='user_dashboard'), 
    
    #Bookings
    path('concerts/<int:concert_id>/book/', views.bookticket, name='bookticket'),
    path('booking_confirmation/<int:concert_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('cancel_ticket/<int:ticket_id>/', views.ticketcancel, name='ticketcancel'),
    path('booking_detail/<int:ticket_id>/', views.booking_detail, name='booking_detail'),
    path('booking-summary/', booking_summary, name='booking_summary'),

    path('ticket/<int:ticket_id>/pdf/', views.ticket_pdf_view, name='ticket_pdf'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),




]
