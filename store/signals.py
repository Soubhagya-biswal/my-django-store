from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, StockNotification, PriceDropNotification, Order,CancellationRequest,ReturnRequest
from django.template.loader import render_to_string
import razorpay

@receiver(pre_save, sender=Product)
def send_stock_notification(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_product = Product.objects.get(pk=instance.pk)
            
            # --- This is the original stock check logic ---
            if old_product.stock == 0 and instance.stock > 0:
                notifications = StockNotification.objects.filter(product=instance)
                for notification in notifications:
                    mail_subject = f"'{instance.name}' is Back in Stock!"
                    message = f"Hi {notification.user.username},\nThe product you wanted, {instance.name}, is now available at MyShop."
                    send_mail(
                        mail_subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [notification.user.email]
                    )
                    notification.delete()

            
            if instance.price < old_product.price:
                price_notifications = PriceDropNotification.objects.filter(product=instance)
                for notification in price_notifications:
                    mail_subject = f"Price Drop Alert for {instance.name}!"
                    message = f"Hi {notification.user.username},\nGood news! The price for '{instance.name}' has dropped to ₹{instance.price}."
                    send_mail(
                        mail_subject,
                        message,
                        settings.EMAIL_HOST_USER,
                        [notification.user.email]
                    )
                    notification.delete()

        except Product.DoesNotExist:
            pass 
@receiver(pre_save, sender=Order)
def send_invoice_on_delivery(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            
            if old_order.status != 'Delivered' and instance.status == 'Delivered':
                user = instance.user
                mail_subject = f"Invoice for Your MyShop Order #{instance.id}"
                
                
                html_message = render_to_string('store/invoice_email.html', {
                    'user': user,
                    'order': instance,
                })
                plain_message = f"Hi {user.username}, Your order #{instance.id} has been delivered. Thank you for shopping with us!"

                send_mail(
                    mail_subject,
                    plain_message, 
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    html_message=html_message, 
                )
        except Order.DoesNotExist:
            pass 
@receiver(pre_save, sender=CancellationRequest)
def process_cancellation_approval(sender, instance, **kwargs):
    print("--- Cancellation signal fired! ---")
    if instance.pk:
        try:
            old_request = CancellationRequest.objects.get(pk=instance.pk)
            print(f"Checking status. Old: {old_request.status}, New: {instance.status}")
            
            # Check if status is changing to 'Approved'
            if old_request.status != 'Approved' and instance.status == 'Approved':
                print("Status changed to Approved. Processing cancellation...")
                order = instance.order
                order.status = 'Cancelled'
                order.save()

                # Check if it was a paid order to process refund
                if order.payment_status == 'Paid':
                    print(f"Paid order #{order.id} detected. Attempting refund...")
                    try:
                        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                        print(f"DEBUG: Attempting refund for payment ID: {order.razorpay_payment_id}")
                        print(f"DEBUG: Refund amount: {int(order.total_amount * 100)}")
                        client.payment.refund(order.razorpay_payment_id, {'amount': int(order.total_amount * 100)})
                        order.payment_status = 'Refunded'
                        order.save()
                        mail_subject = f"Your Order #{order.id} has been Cancelled and Refunded"
                        message = f"Hi {order.user.username},\nYour cancellation request for order #{order.id} has been approved. The amount of ₹{order.total_amount} has been refunded."
                        print("Refund successful.")
                    except Exception as e:
                        print(f"!!! REFUND FAILED for order #{order.id}. Error: {e}")
                        return
                else: # For COD orders
                    print(f"COD order #{order.id} detected. No refund needed.")
                    mail_subject = f"Your Order #{order.id} has been Cancelled"
                    message = f"Hi {order.user.username},\nYour cancellation request for order #{order.id} has been approved."

                # Send the appropriate email
                print(f"Sending cancellation email to {order.user.email}...")
                send_mail(
                    mail_subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [order.user.email]
                )
                print("Email sent successfully.")

        except CancellationRequest.DoesNotExist:
            pass 
@receiver(pre_save, sender=ReturnRequest)
def process_return_approval(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_request = ReturnRequest.objects.get(pk=instance.pk)
            
            if old_request.status != 'Approved' and instance.status == 'Approved':
                order = instance.order
                order.status = 'Returned'
                order.save()
                
                if order.payment_status == 'Paid':
                    try:
                        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                        client.payment.refund(order.razorpay_payment_id, {'amount': int(order.total_amount * 100)})
                        order.payment_status = 'Refunded'
                        order.save()
                        
                        mail_subject = f"Your Order #{order.id} has been Returned and Refunded"
                        message = f"Hi {order.user.username},\nYour return request for order #{order.id} has been approved. The amount of ₹{order.total_amount} has been refunded."
                    except Exception as e:
                        mail_subject = f"Your Order #{order.id} Return Approved, but Refund Failed"
                        message = f"Hi {order.user.username},\nYour return request for order #{order.id} has been approved, but the refund failed. Error: {e}"
                else: # For COD orders
                    mail_subject = f"Your Order #{order.id} has been Returned"
                    message = f"Hi {order.user.username},\nYour return request for order #{order.id} has been approved."

                send_mail(
                    mail_subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [order.user.email]
                )
        except ReturnRequest.DoesNotExist:
            pass