from django.contrib import admin, messages
from .models import (
    Product, Cart, CartItem, Order, OrderItem, 
    StockNotification, Wishlist, PriceDropNotification, Address, CancellationRequest, ReturnRequest, Review,Category,ProductImage,Coupon,DealOfTheDay
)
from django.contrib.sessions.models import Session

from .views import initiate_razorpay_refund, send_cancellation_email,send_refund_processed_email
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse_lazy


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price')
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'payment_mode', 'payment_status', 'status', 'created_at', 'delivered_at']
    list_filter = ['status', 'payment_status', 'payment_mode'] 
    list_editable = ['status', 'payment_status']
    search_fields = ['user__username', 'id', 'razorpay_order_id']
    inlines = [OrderItemInline]
    
    
    def save_model(self, request, obj, form, change):
        
        if 'status' in form.changed_data:
            
            if obj.status == 'Delivered' and not obj.delivered_at:
                obj.delivered_at = timezone.now()
        
       
        super().save_model(request, obj, form, change)



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_best_deal')
    list_filter = ('category', 'is_best_deal')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]
    filter_horizontal = ('related_products',)

    fieldsets = (
        ('Primary Information', {
            'fields': ('name', 'category', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'market_price', 'stock', 'is_best_deal')
        }),
        ('Media & Details', {
            'fields': ('image_url', 'highlights')
        }),
        
        ('AI Stylist ("Complete the Look")', {
            'classes': ('collapse',), 
            'fields': ('related_products',),
        }),
    )

admin.site.register(Session)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(StockNotification)
admin.site.register(Wishlist)
admin.site.register(PriceDropNotification)
admin.site.register(Address)
admin.site.register(Review)
admin.site.register(Category)


@admin.register(CancellationRequest)
class CancellationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_id', 'user_email', 'reason', 'status', 'requested_at']
    list_filter = ['status']
    search_fields = ['order__id', 'order__user__email']

    def approve_and_refund(self, request, queryset):
        successful_requests = 0
        failed_refunds = 0
        
        for cancellation_request in queryset:
            order = cancellation_request.order
            
            if cancellation_request.status == 'Pending':
                
                # Check agar order Razorpay se paid hai
                if order.payment_mode == 'Razorpay' and order.payment_status == 'Paid':
                    
                    refund_successful = initiate_razorpay_refund(order.razorpay_payment_id, order.total_amount)
                    
                    if refund_successful:
                        order.payment_status = 'Refunded'
                        order.status = 'Cancelled'
                        order.save()
                        
                        cancellation_request.status = 'Approved'
                        cancellation_request.save()
                        
                        # --- NAYA CODE: Refund wala email bhejein ---
                        send_cancellation_email(order, refund_processed=True)
                        
                        successful_requests += 1
                    else:
                        failed_refunds += 1
                else:
                    # Agar COD ya unpaid order hai, to sirf status update karo
                    order.status = 'Cancelled'
                    order.save()
                    
                    cancellation_request.status = 'Approved'
                    cancellation_request.save()

                    # --- NAYA CODE: Normal cancellation email bhejein ---
                    send_cancellation_email(order, refund_processed=False)
                    
                    successful_requests += 1
        
        if successful_requests > 0:
            self.message_user(request, f"{successful_requests} cancellation requests were successfully approved.", messages.SUCCESS)
        
        if failed_refunds > 0:
            self.message_user(request, f"{failed_refunds} Razorpay refunds failed. Please check logs and process manually.", messages.ERROR)

    approve_and_refund.short_description = "Approve selected requests and issue refunds"

    actions = [approve_and_refund]

    def order_id(self, obj):
        return obj.order.id
    
    def user_email(self, obj):
        return obj.order.user.email

@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'order', 'status', 'refund_method', 'has_bank_details', 'refund_processed', 'requested_at')
    list_filter = ('status', 'refund_processed', 'refund_method')
    
    
    list_editable = ('status', 'refund_method', 'refund_processed')
    
    search_fields = ('order__id', 'order__user__username', 'bank_account_number')
    
    
    readonly_fields = ('order', 'reason', 'account_holder_name', 'bank_account_number', 'ifsc_code', 'requested_at')
    
    
    fieldsets = (
        ('Request Details & User Bank Info (Read-Only)', {
            'fields': ('order', 'reason', 'requested_at', 'account_holder_name', 'bank_account_number', 'ifsc_code')
        }),
        ('Admin Actions & Notes (Editable)', {
            'fields': ('status', 'refund_method', 'refund_processed', 'admin_comment')
        }),
    )

    
    actions = ['approve_selected_requests', 'mark_refund_as_processed']

    @admin.display(boolean=True, description='Bank Details Provided?')
    def has_bank_details(self, obj):
        return bool(obj.bank_account_number)

    def approve_selected_requests(self, request, queryset):
        updated_count = queryset.filter(status='Pending').update(status='Approved')
        self.message_user(request, f"{updated_count} return request(s) were successfully APPROVED. You can now proceed to Step 2 for refund.", messages.SUCCESS)

    approve_selected_requests.short_description = "Step 1: Approve selected return requests"

    def mark_refund_as_processed(self, request, queryset):
        for rr in queryset.filter(status='Approved', refund_processed=False):
            order = rr.order
            
            def try_sending_email(return_request_obj):
                try:
                    print(f"DEBUG: Email bhejne ki koshish... Order #{return_request_obj.order.id}")
                    send_refund_processed_email(return_request_obj)
                    self.message_user(request, f"Confirmation email for order #{return_request_obj.order.id} sent successfully.", messages.INFO)
                except Exception as e:
                    print(f"!!! EMAIL SENDING FAILED for order #{return_request_obj.order.id}. Error: {e}")
                    self.message_user(request, f"CRITICAL: Refund for order #{return_request_obj.order.id} was processed, but the confirmation email FAILED to send. Please check logs.", messages.ERROR)

            if rr.refund_method == 'Original' and order.payment_mode == 'Razorpay':
                refund_successful = initiate_razorpay_refund(order.razorpay_payment_id, order.total_amount)
                if refund_successful:
                    rr.refund_processed = True
                    order.status = 'Returned'
                    order.payment_status = 'Refunded'
                    rr.save()
                    order.save()
                    self.message_user(request, f"Razorpay refund for order #{order.id} has been initiated successfully.", messages.SUCCESS)
                    try_sending_email(rr) 
                else:
                    self.message_user(request, f"IMPORTANT: Auto-refund for Razorpay order #{order.id} FAILED. Please check logs and process manually.", messages.ERROR)
            else:
                rr.refund_processed = True
                order.status = 'Returned'
                order.payment_status = 'Refunded'
                rr.save()
                order.save()
                self.message_user(request, f"Refund for order #{order.id} has been marked as processed. (Assumed you have paid manually).", messages.SUCCESS)
                try_sending_email(rr) 
    mark_refund_as_processed.short_description = "Step 2: Mark refund as processed (Auto/Manual)"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name', 'discount_percent', 'valid_from', 'valid_to', 'active', 'show_on_homepage')
    list_filter = ('active', 'show_on_homepage', 'valid_to')
    search_fields = ('code', 'display_name')
    list_editable = ('active', 'show_on_homepage') 
@admin.register(DealOfTheDay)
class DealOfTheDayAdmin(admin.ModelAdmin):
    list_display = ('product', 'discount_price', 'end_time', 'active')
    list_filter = ('active', 'end_time')
    search_fields = ('product__name',)
    list_editable = ('active', 'discount_price')
    def save_model(self, request, obj, form, change):
        if obj.active:
            DealOfTheDay.objects.filter(active=True).exclude(pk=obj.pk).update(active=False)
            messages.info(request, "Tabaahi! Is deal ko active karne ke liye, baaki saari deals band kar di gayi hain.")
        super().save_model(request, obj, form, change)
