from auditlog.registry import auditlog
from django.contrib.auth.models import User
from .models import Product, Order, Address, Review

auditlog.register(User)
auditlog.register(Product)
auditlog.register(Order)
auditlog.register(Address)
auditlog.register(Review)
