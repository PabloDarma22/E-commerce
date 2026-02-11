from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product_detail"),
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("cart/add/<int:product_id>/", add_to_cart_view, name="cart_add"),
    path("cart/", cart_detail_view, name="cart_detail"),
    path("cart/remove/<int:item_id>/", remove_cart_item_view, name="cart_remove"),
    path("cart/update/<int:item_id>/", update_cart_item_quantity_view, name="cart_update"),
    path("checkout/", checkout_view, name="checkout"),
    path("checkout/confirm/", checkout_confirm_view, name="checkout_confirm"),
    path("orders/<int:order_id>/", order_detail_view, name="order_detail"),
    path("addresses/", address_list_view, name="address_list"),
    path("addresses/new/", address_create_view, name="address_create"),
    path("addresses/<int:address_id>/default/", address_set_default_view, name="address_set_default"),
    path("addresses/<int:address_id>/delete/", address_delete_view, name="address_delete"),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("orders/<int:order_id>/pay/", order_pay_view, name="order_pay"),

]

