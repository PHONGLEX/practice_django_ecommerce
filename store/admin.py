from django.contrib import admin

from .models import Item, OrderItem, Order, Payment, Coupon, Refund, Address


def make_refund_accepted(modeladmin, request, queryset):
	queryset.update(refund_requested=False, refund_granted=True)
make_refund_accepted.short_description="Update order to refund granted"


admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Refund)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
	prepopulated_fields = {"slug": ("title",)}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("user", "ordered", "being_delivered", "received"
		, "refund_requested", "refund_granted"
		, "billing_address", "shipping_address", "payment", "coupon")
	list_filter = ("ordered", "being_delivered", "received", "refund_requested", "refund_granted")
	list_display_links = ("user", "billing_address", "shipping_address", "payment", "coupon")
	search_fields = ("user__username", "ref_code")
	actions = [make_refund_accepted]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
	list_display = ("user", "street_address", "apartment_address",
			"country", "zip", "address_type", "default")
	list_filter = ("country", "default", "address_type")
	search_fields = ("user_username", "street_address", "apartment_address", "zip")