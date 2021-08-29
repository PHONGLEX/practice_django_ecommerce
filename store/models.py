from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models.signals import post_save
from django_countries.fields import CountryField


CATEGORY_CHOICES = (
	('S', 'Shirt'),
	('SW', 'Sport wear'),
	('OW', 'Outwear'),
)

LABEL_CHOICES = (
	('P', 'primary'),
	('S', 'secondary'),
	('D', 'danger'),
)

ADDRESS_CHOICES = (
	('B', 'Billing'),
	('S', 'Shipping'),
)


class UserProfile(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
	one_click_purchasing = models.BooleanField()

	def __str__(self):
		return self.user.username

def userprofile_receiver(sender, instance, created, *args, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)

post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)


class Item(models.Model):
	title = models.CharField(max_length=100)
	price = models.DecimalField(max_digits=5, decimal_places=2)
	discount_price = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
	label = models.CharField(choices=LABEL_CHOICES, max_length=1)
	slug = models.SlugField()
	description = models.TextField()
	image = models.ImageField(upload_to="images/")

	class Meta:
		verbose_name = "Item"
		verbose_name_plural = "Items"

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse("store:product", kwargs={"slug": self.slug})

	def get_add_to_cart_url(self):
		return reverse("store:add-to-cart", kwargs={"slug": self.slug})

	def get_remove_from_cart_url(self):
		return reverse("store:remove-from-cart", kwargs={"slug": self.slug})

	


class OrderItem(models.Model):
	item = models.ForeignKey(Item, on_delete=models.CASCADE)
	quantity = models.IntegerField(default=1)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	ordered = models.BooleanField(default=False)

	class Meta:
		verbose_name = "OrderItem"
		verbose_name_plural = "OrderItems"

	def __str__(self):
		return f"{self.quantity} of {self.item.title}"

	def get_total_item_price(self):
		return self.item.price * self.quantity

	def get_total_discount_item_price(self):
		return self.item.discount_price * self.quantity

	def get_amount_saved(self):
		return self.get_total_item_price() - self.get_total_discount_item_price()

	def get_final_price(self):
		if self.item.discount_price:
			return self.get_total_discount_item_price()
		return self.get_total_item_price()

	
class Order(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	ref_code = models.CharField(max_length=20, blank=True, null=True)
	ordered = models.BooleanField(default=False)
	items = models.ManyToManyField(OrderItem)
	start_date = models.DateTimeField(auto_now=True)
	ordered_date = models.DateTimeField()
	billing_address = models.ForeignKey("Address", related_name="billing_address", on_delete=models.SET_NULL, blank=True, null=True)
	shipping_address = models.ForeignKey("Address", related_name="shipping_address", on_delete=models.SET_NULL, blank=True, null=True)
	payment = models.ForeignKey("Payment", on_delete=models.SET_NULL, blank=True, null=True)
	coupon = models.ForeignKey("Coupon", on_delete=models.SET_NULL, blank=True, null=True)
	being_delivered = models.BooleanField(default=False)
	received = models.BooleanField(default=False)
	refund_requested = models.BooleanField(default=False)
	refund_granted = models.BooleanField(default=False)

	class Meta:
		verbose_name = "Order"
		verbose_name_plural = "Orders"

	def __str__(self):
		return f"{self.user} - {self.ordered_date.strftime('%Y-%m-%d %H:%M')}"

	def get_total(self):
		total = sum(item.get_final_price() for item in self.items.all())
		if self.coupon:
			return (total - self.coupon.amount)
		return total
	

class Address(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	street_address = models.CharField(max_length=100)
	apartment_address = models.CharField(max_length=100)
	country = CountryField(multiple=False)
	zip = models.CharField(max_length=100)
	address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
	default = models.BooleanField(default=False)

	def __str__(self):
		return self.user.username

	class Meta:
		verbose_name_plural = "Addresses"


class Payment(models.Model):
	stripe_charge_id = models.CharField(max_length=50)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
	amount = models.DecimalField(max_digits=5,decimal_places=2)
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.user.username


class Coupon(models.Model):
	code = models.CharField(max_length=15)
	amount = models.DecimalField(max_digits=5,decimal_places=2)

	def __str__(self):
		return self.code


class Refund(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE)
	reason = models.TextField()
	accepted = models.BooleanField(default=False)
	email = models.EmailField()

	def __str__(self):
		return f"{self.pk}"