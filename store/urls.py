from django.urls import path

from . import views

app_name = "store"


urlpatterns = [
	path('', views.HomeView.as_view(), name="home"),
	path('product/<slug>/', views.ProductDetailView.as_view(), name="product"),
	path('checkout/', views.CheckoutView.as_view(), name="checkout"),
	path('order-summary/', views.OrderSummaryView.as_view(), name="order-summary"),
	path('add-to-cart/<slug>/', views.add_to_cart, name="add-to-cart"),
	path('remove-from-cart/<slug>/', views.remove_from_cart, name="remove-from-cart"),
	path('remove-single-from-cart/<slug>/', views.remove_single_from_cart, name="remove-single-from-cart"),
	path('payment/<payment_option>/', views.PaymentView.as_view(), name="payment"),
	path('add-coupon/', views.AddCouponView.as_view(), name="add-coupon"),
	path('request-refund/', views.RequestRefundView.as_view(), name="request-refund"),
]