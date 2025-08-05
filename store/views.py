# In store/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, CartItem, StockNotification, Wishlist, PriceDropNotification, Order, OrderItem, Address, CancellationRequest,ReturnRequest,Review,Category
from .forms import CustomUserCreationForm, AddressForm, CancellationReasonForm,ReturnReasonForm,ReviewForm,UserProfileUpdateForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.contrib import messages
from django.db.models import Avg, F,ExpressionWrapper, DecimalField
from django.db.models import Q
from django.http import JsonResponse
import datetime
import requests
from requests.exceptions import RequestException 

def get_estimated_delivery_date(pincode):
    today = datetime.date.today()
    hardcoded_pincodes = {
        '751021': {'state': 'Odisha', 'city': 'Bhubaneswar', 'days': 5},
        '110001': {'state': 'Delhi', 'city': 'New Delhi', 'days': 3},
        '400001': {'state': 'Maharashtra', 'city': 'Mumbai', 'days': 3},
    }

    if pincode in hardcoded_pincodes:
        details = hardcoded_pincodes[pincode]
        delivery_days = details['days']
        city = details['city']
        return today + datetime.timedelta(days=delivery_days), city
    
    
    api_url = f"https://api.postalpincode.in/pincode/{pincode}"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0 and data[0]['Status'] == 'Success' and data[0]['PostOffice']:
            post_office = data[0]['PostOffice'][0]
            state = post_office['State']
            city = post_office['District']
            
            
            delivery_days = 7 
            if state in ['Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu']:
                delivery_days = 3
            elif state in ['Uttar Pradesh', 'Bihar', 'Madhya Pradesh', 'Odisha']:
                delivery_days = 5
            
            return today + datetime.timedelta(days=delivery_days), city
            
    except (RequestException, Exception):
        pass
    
    
    return None, None

def homepage(request):
    product_list = Product.objects.all().order_by('id')
    
    
    query = request.GET.get('q')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    category = request.GET.get('category')
    
    # Search logic
    if query:
        product_list = product_list.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    # Filter by price
    if min_price:
        product_list = product_list.filter(price__gte=min_price)
    if max_price:
        product_list = product_list.filter(price__lte=max_price)
    
    if category and category != 'All':
        product_list = product_list.filter(category__name=category)
    
    categories = Category.objects.all()

    
    best_deals = Product.objects.filter(is_best_deal=True)

        
    paginator = Paginator(product_list, 8)
    page_number = request.GET.get('page')
    products_on_page = paginator.get_page(page_number)
    
    context = {
        'products': products_on_page,
        'best_deals': best_deals,
        'categories': categories,
        'selected_category': category,
        'query': query,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'store/index.html', context)

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        
        email = request.POST.get('email')
        
        
        if email and User.objects.filter(email__iexact=email).exists():
            
            messages.error(request, "This email address is already registered. Please use a different one or log in.")
            return render(request, 'store/signup.html', {'form': form})
        

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  
            user.save()

            
            current_site = get_current_site(request)
            mail_subject = 'Activate Your MyShop Account'
            message = render_to_string('store/activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            send_mail(
                mail_subject,
                message,
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            
            return render(request, 'store/check_email.html')
    else:
        form = CustomUserCreationForm()
    
    
    return render(request, 'store/signup.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'store/activation_success.html')
    else:
        return render(request, 'store/activation_invalid.html')
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('homepage')
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})
def logout_request(request):
    logout(request)
    return redirect('homepage')


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Average rating calculate karo
    average_rating = product.reviews.aggregate(Avg('rating'))['rating__avg']
    if average_rating is not None:
        average_rating = round(average_rating, 1)

    is_subscribed = False
    is_wishlisted = False
    is_price_subscribed = False
    user_has_reviewed = False
    
    if request.user.is_authenticated:
        is_subscribed = StockNotification.objects.filter(user=request.user, product=product).exists()
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()
        is_price_subscribed = PriceDropNotification.objects.filter(user=request.user, product=product).exists()
        user_has_reviewed = Review.objects.filter(user=request.user, product=product).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
            
        form = ReviewForm(request.POST)
        if form.is_valid():
            has_delivered_order = OrderItem.objects.filter(
                product=product,
                order__user=request.user,
                order__status='Delivered'
            ).exists()

            if has_delivered_order:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
            else:
                messages.error(request, 'Please buy and receive the product before writing a review.')

            return redirect('product_detail', product_id=product.id)
    else:
        form = ReviewForm()

    reviews = product.reviews.all().order_by('-created_at')
    discount_percent = None
    if product.market_price and product.market_price > product.price:
        # Is line ko update kiya gaya hai taky 100% se zyada na dikhaye
        discount_percent = min(((product.market_price - product.price) / product.market_price) * 100, 99.99)
        discount_percent = round(discount_percent)
    
    context = {
        'product': product,
        'is_subscribed': is_subscribed,
        'is_wishlisted': is_wishlisted,
        'is_price_subscribed': is_price_subscribed,
        'form': form,
        'reviews': reviews,
        'user_has_reviewed': user_has_reviewed,
        'average_rating': average_rating,
        'discount_percent': discount_percent,
    }
    return render(request, 'store/product_detail.html', context)
@login_required
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    
    if request.method == 'POST':
        
        quantity = int(request.POST.get('quantity', 1))
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            
            cart_item.quantity += quantity
        else:
            
            cart_item.quantity = quantity
        
        cart_item.save()
    
    return redirect('product_detail', product_id=product_id)
@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)
@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('view_cart')
@login_required
def increment_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('view_cart')

@login_required
def decrement_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('view_cart')
@login_required
def toggle_stock_notification(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    notification, created = StockNotification.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
       
        notification.delete()
    
    
    return redirect('product_detail', product_id=product_id)
@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        
        wishlist_item.delete()
    
    
    return redirect('product_detail', product_id=product_id)
@login_required
def view_wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'store/wishlist.html', context)
@login_required
def toggle_price_notification(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    notification, created = PriceDropNotification.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        
        notification.delete()
    
    
    return redirect('product_detail', product_id=product_id)
@login_required

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        return redirect('homepage')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    context = {
        'total_price': total_price,
    }
    return render(request, 'store/checkout.html', context)



@login_required
def start_payment(request):
    address_id = request.session.get('address_id')
    if not address_id:
        return redirect('checkout_address')

    shipping_address = get_object_or_404(Address, id=address_id, user=request.user)
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        return redirect('homepage')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    amount_in_paise = int(total_price * 100)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order_data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"order_rcptid_{cart.id}"
    }
    razorpay_order = client.order.create(data=razorpay_order_data)
    
    delivery_date, _ = get_estimated_delivery_date(shipping_address.postal_code)
    
    # --- SAHI CODE START ---
    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        total_amount=total_price,
        payment_mode='Razorpay',
        payment_status='Pending',
        razorpay_order_id=razorpay_order['id'],
        status='Pending',
        estimated_delivery_date=delivery_date
    )
    # --- SAHI CODE END ---

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': amount_in_paise,
        'currency': 'INR',
        'order': order,
        'callback_url': 'http://127.0.0.1:8000/payment-success/'
    }
    
    return render(request, 'store/payment.html', context)
@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        try:
            
            payment_data = request.POST
            razorpay_order_id = payment_data.get('razorpay_order_id', '')
            razorpay_payment_id = payment_data.get('razorpay_payment_id', '')
            razorpay_signature = payment_data.get('razorpay_signature', '')

            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature(params_dict)

            # If verification is successful, update the order
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.payment_status = 'Paid'
            
            # --- Ye line add karni hai ---
            order.razorpay_payment_id = razorpay_payment_id
            
            order.save()

            
            for item in order.items.all():
                Product.objects.filter(id=item.product.id).update(stock=F('stock') - item.quantity)
            Cart.objects.get(user=order.user).delete()

            return render(request, 'store/payment_success.html')

        except Exception as e:
            print(f"Payment verification failed. Error: {e}")
            
            return render(request, 'store/payment_fail.html')
    
    
    return render(request, 'store/payment_fail.html')
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders
    }
    return render(request, 'store/order_history.html', context)
@login_required
def profile(request):
    return render(request, 'store/profile.html')
@login_required
def checkout_address(request):
    addresses = Address.objects.filter(user=request.user)
    form = AddressForm()

    if request.method == 'POST':
        
        if 'use_existing_address' in request.POST:
            address_id = request.POST.get('existing_address')
            if address_id:
                request.session['address_id'] = address_id
                return redirect('checkout')
        else:
            
            form = AddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
                request.session['address_id'] = address.id
                return redirect('checkout')

    context = {
        'addresses': addresses,
        'form': form
    }
    return render(request, 'store/checkout_address.html', context)
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order
    }
    return render(request, 'store/order_detail.html', context)
@login_required
def place_cod_order(request):
    address_id = request.session.get('address_id')
    if not address_id:
        return redirect('checkout_address')

    shipping_address = get_object_or_404(Address, id=address_id, user=request.user)
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        return redirect('homepage')

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    delivery_date, _ = get_estimated_delivery_date(shipping_address.postal_code)

    # --- SAHI CODE START ---
    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        total_amount=total_price,
        payment_mode='COD',
        payment_status='Pending',
        status='Processing',
        estimated_delivery_date=delivery_date
    )
    # --- SAHI CODE END ---

    # Create OrderItems for the Order
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )
        
    for item in order.items.all():
        Product.objects.filter(id=item.product.id).update(stock=F('stock') - item.quantity)
    
    
    cart.delete()

    
    return render(request, 'store/payment_success.html')
@login_required
def request_cancellation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    
    if CancellationRequest.objects.filter(order=order).exists():
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        form = CancellationReasonForm(request.POST)
        if form.is_valid():
            cancellation_request = form.save(commit=False)
            cancellation_request.order = order
            cancellation_request.save()
            return redirect('order_detail', order_id=order.id)
    else:
        form = CancellationReasonForm()

    context = {
        'form': form,
        'order': order
    }
    return render(request, 'store/request_cancellation.html', context)
@login_required
def request_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if the order is eligible for return: status should be 'Delivered' and payment 'Paid'.
    if order.status != 'Delivered' or order.payment_status != 'Paid':
        return redirect('order_detail', order_id=order.id)
    
    # Check if a return request already exists
    if hasattr(order, 'return_request'):
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        form = ReturnReasonForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.save()
            
            
            order.status = 'Return Requested'
            order.save()
            return redirect('order_detail', order_id=order.id)
    else:
        form = ReturnReasonForm()

    context = {
        'form': form,
        'order': order
    }
    return render(request, 'store/request_return.html', context)
@login_required
def my_reviews(request):
    reviews = Review.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'reviews': reviews,
    }
    return render(request, 'store/my_reviews.html', context)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        review.delete()
    return redirect('my_reviews')
def check_delivery(request):
    if request.method == 'POST':
        pincode = request.POST.get('pincode')
        
        # Pincode validation add ki gayi hai
        if not pincode or not pincode.isdigit() or len(pincode) != 6:
            return JsonResponse({'error': 'Invalid pincode format.'})
            
        delivery_date, city = get_estimated_delivery_date(pincode)

        if city:
            return JsonResponse({'estimated_date': delivery_date.strftime('%d %B, %Y'), 'city': city})
        else:
            return JsonResponse({'error': 'Could not check delivery for this pincode.'})
            
    return JsonResponse({'error': 'Invalid request'}, status=400)
def initiate_razorpay_refund(payment_id, amount):
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_in_paise = int(amount * 100)
        
        # Razorpay refund API call
        refund = client.payment.refund(payment_id, {'amount': amount_in_paise})
        
        # Check if refund was processed
        if refund and refund.get('status') == 'processed':
            return True
        else:
            print(f"Razorpay refund status was not 'processed': {refund}")
            return False
            
    except Exception as e:
        # Agar koi error aaye to use print karo
        print(f"Razorpay refund failed for payment_id {payment_id}: {e}")
        return False
def send_cancellation_email(order, refund_processed=False):
    """
    Sends an email to the user confirming order cancellation.
    Includes refund details if a refund was processed.
    """
    mail_subject = f'Your Order #{order.id} has been Cancelled'
    
    # Prepare context for the email template
    context = {
        'order': order,
        'refund_processed': refund_processed, # Ye batayega ki refund hua ya nahi
    }
    
    # Render the email content from an HTML template
    # Hum ye template agle step mein banayenge
    html_message = render_to_string('store/emails/cancellation_confirmation.html', context)
    
    # Send the email
    send_mail(
        subject=mail_subject,
        message='', 
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[order.user.email],
        html_message=html_message, 
        fail_silently=False,
    )
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileUpdateForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'store/edit_profile.html', context)