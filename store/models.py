from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Category Image URL")

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField("Market Price", max_digits=10, decimal_places=2, null=True, blank=True)
    market_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    is_best_deal = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    highlights = models.TextField(blank=True, null=True, help_text="Enter each highlight on a new line.")
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Main Product Image URL")
    stock = models.PositiveIntegerField(default=0)
    
    related_products = models.ManyToManyField(
        'self', 
        blank=True, 
        symmetrical=False,
        verbose_name="Related Products (for 'Complete the Look')",
        help_text="Select products that go well with this item."
    )
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image_url = models.URLField(max_length=1024, blank=True, null=True, verbose_name="Gallery Image URL")

    def __str__(self):
        return f"Image for {self.product.name}"



class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)


    def __str__(self):
        return f"{self.quantity} of {self.product.name}"
class StockNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('user', 'product')


    def __str__(self):
        return f"{self.user.username} wants {self.product.name}"
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('user', 'product')


    def __str__(self):
        return f"{self.product.name} in {self.user.username}'s wishlist"
class PriceDropNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('user', 'product')


    def __str__(self):
        return f"{self.user.username} wants price drop for {self.product.name}"

ORDER_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Shipped', 'Shipped'),
    ('Out for Delivery', 'Out for Delivery'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
    ('Returned', 'Returned'),
]
PAYMENT_MODE_CHOICES = [
    ('COD', 'Cash on Delivery'),
    ('Razorpay', 'Razorpay'),
]
PAYMENT_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Paid', 'Paid'),
    ('Refunded', 'Refunded'), 
    ('COD', 'COD'),
]
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='COD')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending') 
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)


    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"{self.quantity} of {self.product.name}"
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)


    def __str__(self):
        return f"{self.street_address}, {self.city}, {self.user.username}"
CANCELLATION_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
]


class CancellationRequest(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=CANCELLATION_STATUS_CHOICES, default='Pending')
    requested_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Cancellation request for Order #{self.order.id}"
RETURN_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected'),
]
REFUND_METHOD_CHOICES = [
    ('Original', 'Refund to Original Payment Method'),
    ('Bank', 'Refund to Bank Account'),
]

class ReturnRequest(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='return_request')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='Pending')
    requested_at = models.DateTimeField(auto_now_add=True)

   
    refund_method = models.CharField(max_length=20, choices=REFUND_METHOD_CHOICES, null=True, blank=True)
    
    
    account_holder_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Account Holder Name")
    bank_account_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Bank Account Number")
    ifsc_code = models.CharField(max_length=20, null=True, blank=True, verbose_name="IFSC Code")
    
    
    admin_comment = models.TextField(null=True, blank=True, help_text="Internal notes for this return.")
    refund_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Return request for Order #{self.order.id} - {self.status}"

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('product', 'user') 
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="The coupon code customers will enter (e.g., 'SALE50').")
    display_name = models.CharField(max_length=100, help_text="Text to display on the homepage deal (e.g., 'Special Diwali Offer').")
    valid_from = models.DateTimeField(help_text="The date and time from which the coupon is valid.")
    valid_to = models.DateTimeField(help_text="The date and time until which the coupon is valid.")
    discount_percent = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (e.g., 15 for 15%)."
    )
    active = models.BooleanField(default=True, help_text="Is the coupon currently active?")
    show_on_homepage = models.BooleanField(default=False, help_text="Check this to show the coupon deal on the homepage.")

    class Meta:
        ordering = ['-valid_to'] 

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"
    
class DealOfTheDay(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, help_text="Select the product for the deal.")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The special discounted price for the deal.")
    end_time = models.DateTimeField(help_text="The date and time when this deal will end.")
    active = models.BooleanField(default=True, help_text="Is this deal currently active?")

    class Meta:
        verbose_name_plural = "Deal of the Day"

    def __str__(self):
        return f"Deal on {self.product.name} until {self.end_time.strftime('%Y-%m-%d %H:%M')}"
class UserActivity(models.Model):
    
    ACTIVITY_TYPES = [
        ('product_view', 'Product View'),
        ('category_view', 'Category View'),
        ('add_to_cart', 'Add to Cart'),
        ('search', 'Search'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    
   
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    
    search_query = models.CharField(max_length=255, null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            actor = self.user.username
        else:
            actor = f"Guest (Session: {self.session_key[:6]}...)"
        
        if self.product:
            return f"{actor} - {self.activity_type} - {self.product.name}"
        elif self.category:
            return f"{actor} - {self.activity_type} - {self.category.name}"
        elif self.search_query:
            return f"{actor} - {self.activity_type} - '{self.search_query}'"
        else:
            return f"{actor} - {self.activity_type}"