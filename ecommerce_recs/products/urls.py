from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.catalog, name='catalog'),
    path('trending/', views.trending, name='trending'),
    path('cart/', views.view_cart, name='cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('wishlist/', views.view_wishlist, name='wishlist'),
    path('<str:asin>/wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    path('checkout/', views.checkout_page, name='checkout'),
    path('checkout/place-order/', views.place_order, name='place_order'),
    path('checkout/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
    path('<str:asin>/', views.detail, name='detail'),
    path('<str:asin>/add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('<str:asin>/add_review/', views.add_review, name='add_review'),
]
