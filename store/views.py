from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import View
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund
from .forms import CheckoutForm, CouponForm, RefundForm
import stripe
import random
import string


def create_ref_code():
	return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
	items = Item.objects.all()
	context = {
		"items": items
	}
	return render(request, "products.html", context)


def is_valid_form(values):
	valid = True
	for field in values:
		if field == "":
			valid = False
	return valid


class ProductDetailView(DetailView):
	model = Item
	template_name = "product.html"


class HomeView(ListView):
	template_name = "home.html"
	model = Item
	context_object_name = "items"
	paginate_by = 10


class OrderSummaryView(LoginRequiredMixin, View):

	def get(self, *args, **kwargs):
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			context = {
				"object": order
			}
		except ObjectDoesNotExist:
			messages.warning(self.request, "You do not have an active order")
			return redirect("/")
		return render(self.request, "order_summary.html", context)


class CheckoutView(View):
	def get(self, *args, **kwargs):
		form = CheckoutForm()
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			context = {
				"form": form,
				"order": order,
				"couponform": CouponForm(),
				'DISPLAY_COUPON_FORM': True,
			}


			shipping_address = Address.objects.filter(
				user=self.request.user,
				address_type="S",
				default=True
			)
			if shipping_address.exists():
				context.update({"default_shipping_address": shipping_address[0]})

			billing_address = Address.objects.filter(
				user=self.request.user,
				address_type="B",
				default=True
			)
			if shipping_address.exists():
				context.update({"default_billing_address": billing_address[0]})

			return render(self.request, "checkout.html", context)
		except ObjectDoesNotExist:
			messages.warning(self.request, "You do not have an active order")
			return redirect("store:checkout")
		

	def post(self, *args, **kwargs):
		form = CheckoutForm(self.request.POST or None)
		try:
			order = Order.objects.get(user=self.request.user, ordered=False)
			if form.is_valid():
				use_default_shipping = form.cleaned_data.get("use_default_shipping")
				if use_default_shipping:
					print("Using the default shipping address")
					address_qs = Address.objects.filter(
										user=self.request.user,
										address_type="S",
										default=True
									)
					if address_qs.exists():
						shipping_address = address_qs[0]
					else:
						messages.info(self.request, "No default shipping address available")
						return redirect("store:checkout")
				else:
					print("User is entering a new shipping address")

					shipping_address1 = form.cleaned_data.get("shipping_address")
					shipping_address2 = form.cleaned_data.get("shipping_address2")
					shipping_country = form.cleaned_data.get("shipping_country")
					shipping_zip = form.cleaned_data.get("shipping_zip")

					if is_valid_form([shipping_address1,shipping_address2,shipping_country,shipping_zip]):
						shipping_address = Address.objects.create(
							user=self.request.user,
							street_address=shipping_address1,
							apartment_address=shipping_address2,
							country=shipping_country,
							zip=shipping_zip,
							address_type="S"
						)
						
						set_default_shipping = form.cleaned_data.get('set_default_shipping')
						if set_default_shipping:
							shipping_address.default = True
							shipping_address.save()	
					else:
						messages.info(self.request, "Please fill in the required shipping address fields")		
				
				order.shipping_address = shipping_address
				order.save()
				use_default_billing = form.cleaned_data.get("use_default_billing")
				same_billing_address = form.cleaned_data.get("same_billing_address")

				if same_billing_address:
					billing_address = shipping_address
					billing_address.pk = None
					billing_address.save()
					billing_address.address_type = "B"
					billing_address.save()
					order.billing_address = billing_address
					order.save()

				elif use_default_billing:
					print("Using the default billing address")
					address_qs = Address.objects.filter(
										user=self.request.user,
										address_type="B",
										default=True
									)
					if address_qs.exists():
						billing_address = address_qs[0]
					else:
						messages.info(self.request, "No default billing address available")
						return redirect("store:checkout")
				else:
					print("User is entering a new billing address")

					billing_address1 = form.cleaned_data.get("billing_address")
					billing_address2 = form.cleaned_data.get("billing_address2")
					billing_country = form.cleaned_data.get("billing_country")
					billing_zip = form.cleaned_data.get("billing_zip")

					if is_valid_form([billing_address1,billing_address2,billing_country,billing_zip]):
						billing_address = Address.objects.create(
							user=self.request.user,
							street_address=billing_address1,
							apartment_address=billing_address2,
							country=billing_country,
							zip=billing_zip,
							address_type="B"
						)
						
						set_default_billing = form.cleaned_data.get('set_default_billing')
						if set_default_billing:
							billing_address.default = True
							billing_address.save()	
					else:
						messages.info(self.request, "Please fill in the required billing address fields")
				order.billing_address = billing_address
				order.save()	
				payment_option = form.cleaned_data.get("payment_option")

				if payment_option == "S":
					return redirect("store:payment", payment_option="stripe")
				elif payment_option == "P":
					return redirect("store:payment", payment_option="paypal")
				else:
					messages.warning(self.request, "Invalid payment option")
					return redirect("store:order-summary")
			messages.warning(self.request, "Failed to checkout")
			return redirect('store:checkout')
		except ObjectDoesNotExist:
			messages.warning(self.request, "You do not have an active order")
			return redirect("store:order-summary")


class PaymentView(View):
	def get(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		if order.billing_address:
			context = {
				'stripe_pub_key': settings.STRIPE_PUBLISH_KEY,
				'order': order,
				'DISPLAY_COUPON_FORM': False,
			}
			return render(self.request, "payment.html", context)
		else:
			messages.warning(self.request, "You have not added a billing address")
			return redirect("store:checkout")

	def post(self, *args, **kwargs):
		order = Order.objects.get(user=self.request.user, ordered=False)
		token = self.request.POST.get("stripe_token")
		amount = int(order.get_total() * 100)
		
		try:
			stripe.api_key = settings.STRIPE_SECRET_KEY
			charge = stripe.Charge.create(
				amount=amount,
				currency="usd",
				source=token
			)
			
			# create payment
			payment = Payment()
			payment.stripe_charge_id = charge['id']
			payment.user = self.request.user
			payment.amount = order.get_total()
			payment.save()

			order_items = order.items.all()
			order_items.update(ordered=True)
			for item in order_items:
				item.save()

			order.ordered = True
			order.payment = payment
			order.ref_code = create_ref_code()
			order.save()

			messages.success(self.request, "Your order was successfully")

			return redirect("/")

		except stripe.error.CardError as e:
			print(e)
			body = e.json_body
			err = body.get('error', {})
			messages.warning(self.request, f"{err.get('message')}")
		except stripe.error.RateLimitError as e:
			print(e)
			messages.warning(self.request, "Rate limit error")
		except stripe.error.InvalidRequestError as e:
			print(e)
			messages.warning(self.request, "Invalid parameters")
		except stripe.error.AuthenticationError as e:
			print(e)
			messages.warning(self.request, "Not authenticated")
		except stripe.error.APIConnectionError as e:
			print(e)
			messages.warning(self.request, "Network error")
		except stripe.error.StripeError as e:
			print(e)
			messages.warning(self.request, "Something went wrong. You were not charged. Please try again")
		except Exception as e:
			print(e)
			messages.warning(self.request, "A serious error occurred. We have been notified.")
		


@login_required
def add_to_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_item, _ = OrderItem.objects.get_or_create(item=item, user=request.user, ordered=False)
	order_qs = Order.objects.filter(user=request.user, ordered=False)

	if order_qs.exists():
		order = order_qs[0]

		if order.items.filter(item__slug=item.slug).exists():
			order_item.quantity += 1
			order_item.save()
			messages.info(request, "This item quantity was updated.")
			return redirect("store:order-summary")
		else:
			messages.info(request, "This item was added to your cart.")
			order.items.add(order_item)
			return redirect("store:order-summary")
	else:
		ordered_date = timezone.now()
		order = Order.objects.create(user=request.user, ordered_date=ordered_date)
		order.items.add(order_item)
		messages.info(request, "This item was added to your cart.")
		return redirect("store:order-summary")


@login_required	
def remove_from_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_qs = Order.objects.filter(user=request.user, ordered=False)
	if order_qs.exists():
		order = order_qs[0]
		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			order.items.remove(order_item)
			order_item.delete()
			messages.info(request, "This item was removed from your cart")
			return redirect("store:order-summary")
		else:
			messages.info(request, "This item was not in your cart")
			return redirect("store:product", slug=item.slug)
	else:
		messages.info(request, "You do not have an active order")
		return redirect("store:product", slug=slug)


@login_required	
def remove_single_from_cart(request, slug):
	item = get_object_or_404(Item, slug=slug)
	order_qs = Order.objects.filter(user=request.user, ordered=False)
	if order_qs.exists():
		order = order_qs[0]
		if order.items.filter(item__slug=item.slug).exists():
			order_item = OrderItem.objects.filter(
				item=item,
				user=request.user,
				ordered=False
			)[0]
			order_item.quantity -= 1
			order_item.save()

			if order_item.quantity <= 0:
				order_item.delete()
			messages.info(request, "This item quantity was updated")
			return redirect("store:order-summary")
		else:
			messages.info(request, "This item was not in your cart")
			return redirect("store:product", slug=item.slug)
	else:
		messages.info(request, "You do not have an active order")
		return redirect("store:product", slug=slug)


def get_coupon(request, code):
	try:
		coupon = Coupon.objects.get(code=code)
		return coupon
	except ObjectDoesNotExist:
		messages.info(request, "This coupon does not exist")
		return redirect("store:checkout")


class AddCouponView(View):
	def post(self, *args, **kwargs):
		form = CouponForm(self.request.POST or None)
		if form.is_valid():
			try:
				code = form.cleaned_data.get('code')
				order = Order.objects.get(user=self.request.user, ordered=False)
				order.coupon = get_coupon(self.request, code)
				order.save()
				messages.success(self.request, "Successfully added coupon")
				return redirect("store:checkout")
			except ObjectDoesNotExist:

				return redirect("store:checkout")


class RequestRefundView(View):
	def get(self, *args, **kwargs):
		form = RefundForm()
		context = {
			"form": form
		}
		return render(self.request, "request_refund.html", context)

	def post(self, *args, **kwargs):
		form = RefundForm(self.request.POST or None)
		if form.is_valid():
			ref_code = form.cleaned_data.get('ref_code') 
			message = form.cleaned_data.get('message')
			email = form.cleaned_data.get('email')
			print(ref_code)
			try:
				order = Order.objects.get(ref_code=ref_code)
				order.refund_requested = True
				order.save()

				refund = Refund.objects.create(
					order=order,
					reason=message,
					email=email
				)

				messages.info(self.request, "Your request was received")
				return redirect("store:request-refund")
			except ObjectDoesNotExist:
				messages.info(self.request, "This order doest not exist")
				return redirect("store:request-refund")