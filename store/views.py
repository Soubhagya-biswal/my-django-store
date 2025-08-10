# In store/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Cart, CartItem, StockNotification, Wishlist, PriceDropNotification, Order, OrderItem, Address, CancellationRequest,ReturnRequest,Review,Category,Coupon,DealOfTheDay
from .forms import CustomUserCreationForm, AddressForm, CancellationReasonForm,ReturnRequestForm,ReviewForm,UserProfileUpdateForm,CouponApplyForm
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
from django.db.models import Sum, Avg, F,ExpressionWrapper, DecimalField
from django.db.models import Q
from django.http import JsonResponse
import datetime
import requests
from requests.exceptions import RequestException 
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.clickjacking import xframe_options_sameorigin
import json
import google.generativeai as genai
import os
from django.urls import reverse


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
    
    if query:
        product_list = product_list.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if min_price:
        product_list = product_list.filter(price__gte=min_price)
    if max_price:
        product_list = product_list.filter(price__lte=max_price)
    if category and category != 'All':
        product_list = product_list.filter(category__name=category)
        
    categories = Category.objects.all()
    best_deals = Product.objects.filter(is_best_deal=True)
    
    now = timezone.now()
    homepage_coupons = Coupon.objects.filter(
        active=True,
        show_on_homepage=True,
        valid_from__lte=now,
        valid_to__gte=now
    )
    deal_of_the_day = None
    deal_discount_percent = 0
    try:
        deal_of_the_day = DealOfTheDay.objects.get(active=True, end_time__gte=now)
        original_price = deal_of_the_day.product.market_price or deal_of_the_day.product.price
        if original_price > 0:
            deal_discount_percent = round(((original_price - deal_of_the_day.discount_price) / original_price) * 100)
    except DealOfTheDay.DoesNotExist:
        deal_of_the_day = None
            
    if deal_of_the_day:
        deal_product_id = deal_of_the_day.product.id
        deal_price = deal_of_the_day.discount_price

        for product in best_deals:
            if product.id == deal_product_id:
                product.price = deal_price

        
        for product in product_list:
            if product.id == deal_product_id:
                product.price = deal_price


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
        'homepage_coupons': homepage_coupons,
        'deal_of_the_day': deal_of_the_day,
        'deal_discount_percent': deal_discount_percent,
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
    now = timezone.now()
    try:
        deal = DealOfTheDay.objects.get(product=product, active=True, end_time__gte=now)
        product.price = deal.discount_price
    except DealOfTheDay.DoesNotExist:
        pass

    discount_percent = None
    if product.market_price and product.market_price > product.price:
        
        discount_percent = min(((product.market_price - product.price) / product.market_price) * 100, 99.99)
        discount_percent = round(discount_percent)
        
    seven_days_ago = timezone.now() - timedelta(days=7)
    sales_last_7_days = OrderItem.objects.filter(
        product=product, order__created_at__gte=seven_days_ago, order__status='Delivered'
    ).aggregate(total_sold=Sum('quantity'))['total_sold'] or 0

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
        'sales_last_7_days': sales_last_7_days,

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
    now = timezone.now()
    total_price = 0
    for item in cart_items:
        try:
            deal = DealOfTheDay.objects.get(product=item.product, active=True, end_time__gte=now)
            item.current_price = deal.discount_price
        except DealOfTheDay.DoesNotExist:
            item.current_price = item.product.price
        total_price += item.current_price * item.quantity


    coupon_apply_form = CouponApplyForm()
    coupon = None
    discount_amount = 0
    final_price = total_price
    coupon_id = request.session.get('coupon_id')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            
            discount_amount = (total_price * coupon.discount_percent) / 100
            final_price = total_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_id']
            messages.error(request, "The applied coupon is no longer valid.")

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'coupon_apply_form': coupon_apply_form, 
        'coupon': coupon, 
        'discount_amount': discount_amount, 
        'final_price': final_price, 
    }
    return render(request, 'store/cart.html', context)

@login_required
def apply_coupon(request):
    now = timezone.now()
    if request.method == 'POST':
        form = CouponApplyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                coupon = Coupon.objects.get(
                    code__iexact=code, 
                    active=True, 
                    valid_from__lte=now, 
                    valid_to__gte=now
                )
                request.session['coupon_id'] = coupon.id
                messages.success(request, f'Coupon "{coupon.code}" applied successfully!')
            except Coupon.DoesNotExist:
                request.session['coupon_id'] = None
                messages.error(request, 'This coupon is invalid or has expired.')
    return redirect('view_cart')
@login_required
def remove_coupon(request):
    
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
        messages.success(request, 'Coupon has been removed.')
    
    
    return redirect('view_cart')
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
    now = timezone.now()
    total_price = 0
    for item in cart_items:
        try:
            deal = DealOfTheDay.objects.get(product=item.product, active=True, end_time__gte=now)
            item_price = deal.discount_price
        except DealOfTheDay.DoesNotExist:
            item_price = item.product.price
        total_price += item_price * item.quantity

    coupon = None
    discount_amount = 0
    final_price = total_price

    coupon_id = request.session.get('coupon_id')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            discount_amount = (total_price * coupon.discount_percent) / 100
            final_price = total_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_id']
            messages.error(request, "The coupon you had applied is no longer valid and has been removed.")
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'coupon': coupon,
        'discount_amount': discount_amount,
        'final_price': final_price,
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

    now = timezone.now()
    total_price = 0
    for item in cart_items:
        try:
            deal = DealOfTheDay.objects.get(product=item.product, active=True, end_time__gte=now)
            item_price = deal.discount_price
        except DealOfTheDay.DoesNotExist:
            item_price = item.product.price
        total_price += item_price * item.quantity

    final_price = total_price
    coupon_id = request.session.get('coupon_id')

    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            discount_amount = (total_price * coupon.discount_percent) / 100
            final_price = total_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_id']
            messages.error(request, "The coupon applied is invalid. Please review your order.")
            return redirect('view_cart')

    amount_in_paise = int(final_price * 100)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order_data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"order_rcptid_{cart.id}"
    }
    razorpay_order = client.order.create(data=razorpay_order_data)

    delivery_date, _ = get_estimated_delivery_date(shipping_address.postal_code)
    
    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        total_amount=final_price,
        payment_mode='Razorpay',
        payment_status='Pending',
        razorpay_order_id=razorpay_order['id'],
        status='Pending',
        estimated_delivery_date=delivery_date
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price 
        )
    callback_url = request.build_absolute_uri(reverse('payment_success'))

    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': amount_in_paise,
        'currency': 'INR',
        'order': order,
        'callback_url': callback_url  
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
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.payment_status = 'Paid'
            order.razorpay_payment_id = razorpay_payment_id
            order.save()
            for item in order.items.all():
                Product.objects.filter(id=item.product.id).update(stock=F('stock') - item.quantity)
            
            Cart.objects.get(user=order.user).delete()
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
                
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
    is_return_eligible = False
    return_window_expired = False
    return_deadline = None
    has_existing_return_request = ReturnRequest.objects.filter(order=order).exists()
    
    if not has_existing_return_request and order.status == 'Delivered' and order.delivered_at:
        return_deadline = order.delivered_at + timedelta(days=7)
        if timezone.now() <= return_deadline:
            is_return_eligible = True
        else:
            return_window_expired = True

    
    has_existing_cancellation_request = CancellationRequest.objects.filter(order=order).exists()

    context = {
        'order': order,
        
        
        'is_return_eligible': is_return_eligible,
        'return_window_expired': return_window_expired,
        'return_deadline': return_deadline,
        'has_existing_return_request': has_existing_return_request,
        
        
        'has_existing_cancellation_request': has_existing_cancellation_request,
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

    
    now = timezone.now()
    total_price = 0
    for item in cart_items:
        try:
            deal = DealOfTheDay.objects.get(product=item.product, active=True, end_time__gte=now)
            item_price = deal.discount_price
        except DealOfTheDay.DoesNotExist:
            item_price = item.product.price
        total_price += item_price * item.quantity
    
    final_price = total_price
    
    coupon_id = request.session.get('coupon_id')
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            discount_amount = (total_price * coupon.discount_percent) / 100
            final_price = total_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_id']
            messages.error(request, "The coupon applied is invalid. Please review your order.")
            return redirect('view_cart')
            
    delivery_date, _ = get_estimated_delivery_date(shipping_address.postal_code)

    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        total_amount=final_price,  
        payment_mode='COD',
        payment_status='Pending',
        status='Processing',
        estimated_delivery_date=delivery_date
    )

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
    if 'coupon_id' in request.session:
        del request.session['coupon_id']

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
# views.py mein yeh naya request_return function paste karein

def request_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Security Check: Yahan hum 'delivered_at' ka istemal kar rahe hain
    is_eligible = (
        order.status == 'Delivered' and 
        order.delivered_at and 
        (timezone.now() - order.delivered_at) <= timedelta(days=7)
    )

    if not is_eligible:
        messages.error(request, 'This order is not eligible for a return.')
        return redirect('order_detail', order_id=order.id)
    
    # ... Neeche aapka form handling ka purana code waisa hi rahega ...
    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.save()
            messages.success(request, 'Your return request has been submitted.')
            return redirect('order_detail', order_id=order.id)
    else:
        form = ReturnRequestForm()

    return render(request, 'store/request_return.html', {'form': form, 'order': order})


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
    
    
    context = {
        'order': order,
        'refund_processed': refund_processed, 
    }
    
    
    html_message = render_to_string('store/emails/cancellation_confirmation.html', context)
    
    
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
def send_refund_processed_email(return_request):
    """
    Yeh function user ko email bhejta hai jab refund process ho jaata hai.
    """
    order = return_request.order
    subject = f"Refund Processed for Your Order #{order.id}"
    html_message = render_to_string('store/emails/refund_processed_email.html', {
        'order': order,
        'return_request': return_request
    })
    
    
    plain_message = f"Hi {order.user.username}, your refund for order #{order.id} has been processed."
    
    from_email = 'atozstore722@gmail.com'  
    to_email = order.user.email
    
    try:
        send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
        return True
    except Exception as e:
        print(f"Email sending failed for order {order.id}: {e}")
        return False

@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    today = timezone.now().date()
    total_revenue = Order.objects.filter(status='Delivered').aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders_count = Order.objects.count()
    total_customers_count = User.objects.count()
    revenue_today = Order.objects.filter(status='Delivered', created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    orders_today_count = Order.objects.filter(created_at__date=today).count()
    customers_today_count = User.objects.filter(date_joined__date=today).count()
    recent_orders = Order.objects.order_by('-created_at')[:5]

    context = {
        'total_revenue': total_revenue,
        'total_orders_count': total_orders_count,
        'total_customers_count': total_customers_count,
        'revenue_today': revenue_today,
        'orders_today_count': orders_today_count,
        'customers_today_count': customers_today_count,
        'recent_orders': recent_orders,
    }
    return render(request, 'store/admin_dashboard.html', context)

@xframe_options_sameorigin 
@user_passes_test(lambda u: u.is_superuser)
def sales_chart_iframe(request):
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)
    sales_data = Order.objects.filter(status='Delivered', created_at__date__gte=seven_days_ago).values('created_at__date').annotate(daily_revenue=Sum('total_amount')).order_by('created_at__date')
    
    sales_dict = {item['created_at__date']: item['daily_revenue'] for item in sales_data}
    chart_labels = []
    chart_data = []
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        chart_labels.append(date.strftime('%b %d'))
        chart_data.append(float(sales_dict.get(date, 0)))

    context = {
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'store/sales_chart_iframe.html', context)
genai.configure(api_key=settings.GOOGLE_API_KEY)

@csrf_exempt
def ask_ai_buddy(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            question = data.get('question')

            if not product_id or not question:
                return JsonResponse({'answer': 'Error: Missing product ID or question.'}, status=400)

            file_path = os.path.join(settings.BASE_DIR, 'ai_data', 'product_knowledge_base.json')
            with open(file_path, 'r') as f:
                knowledge_base = json.load(f)
            product = Product.objects.get(id=int(product_id))
            product_info = next((p for p in knowledge_base if p['id'] == product.id), None)

            if not product_info:
                return JsonResponse({'answer': 'Sorry, my knowledge base does not have information about this product yet. Please try running the prepare_ai_data command.'}, status=404)

            related_products = product.related_products.all()
            related_products_names = [p.name for p in related_products]
            related_products_text = ", ".join(related_products_names) if related_products_names else "None"

            prompt = f"""
            You are 'Tech Dost', a super-smart and friendly AI assistant for an e-commerce website. Your goal is to help customers and boost sales.

            **1. Information about the product the customer is viewing:**
            - Product Name: {product_info.get('name')}
            - Description: {product_info.get('description')}
            - Highlights: {product_info.get('highlights')}
            - Current Price: {product_info.get('price')} INR
            - Market Price (MRP): {product_info.get('market_price', 'N/A')} INR
            - Discount: {product_info.get('discount_percentage', 0)}%
            - Stock: {product_info.get('stock')} units available
            - Frequently Bought Together: {related_products_text}

            **2. General Store Information (Use this for general questions):**
            - **Payment Options:** We accept all online payments like Credit/Debit Card and UPI. We also have a Cash on Delivery (COD) option available for most locations.
            - **Wishlist:** To add a product to your wishlist, just click the heart icon (♡) that you see on the product page. It's very simple!
            - **Returns:** We have a 7-day return policy. If you don't like the product, you can easily return it.
            - **Delivery:** Our standard delivery usually takes 3 to 5 business days.

            **The customer's question is: "{question}"**

            **Your Task (Follow these rules strictly):**
            1.  First, try to answer the question using the **"Information about the product"**.
            2.  If the answer is not in the product information, use the **"General Store Information"**.
            3.  Answer in a very friendly, human-like, and short manner. Address the user as 'dost' or 'bhai'.
            4.  After answering, if it feels natural and the customer isn't asking about a problem, you can suggest ONE of the 'Frequently Bought Together' items.
            5.  If the customer asks about a discount, use the 'Discount' percentage. If the discount is 0%, say there are no special discounts right now.
            6.  If you absolutely cannot answer, say: "Bhai, iske baare mein mujhe theek se nahi pata. Aap humari support team se pooch sakte hain."
            """

            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            
            ai_answer = response.text.strip()
            
            return JsonResponse({'answer': ai_answer})

        except Product.DoesNotExist:
             return JsonResponse({'answer': 'Sorry, this product does not seem to exist in our main database.'}, status=404)
        except Exception as e:
            error_message = f"Oops! AI Buddy is taking a nap. Error: {str(e)}"
            return JsonResponse({'answer': error_message}, status=500)

    return JsonResponse({'answer': 'Invalid request method.'}, status=405)
def ai_chat_page(request):
    """
    Yeh function bas humare naye, general AI Chat Room ke 'chehre' (HTML page) ko dikhata hai.
    """
    return render(request, 'store/ai_chat_page.html')
