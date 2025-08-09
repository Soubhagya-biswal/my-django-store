from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('ai-chat/', views.ai_chat_page, name='ai_chat_page'),
    path('sales-chart-iframe/', views.sales_chart_iframe, name='sales_chart_iframe'),
    path('signup/', views.signup, name='signup'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('login/', views.login_view, name='login'),
    
    
    path('logout/', views.logout_request, name='logout'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('ask-ai/', views.ask_ai_buddy, name='ask_ai'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/address/', views.checkout_address, name='checkout_address'),
    path('cart/', views.view_cart, name='view_cart'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('checkout/', views.checkout, name='checkout'),
    path('start-payment/', views.start_payment, name='start_payment'),
    path('place-cod-order/', views.place_cod_order, name='place_cod_order'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('increment-item/<int:item_id>/', views.increment_cart_item, name='increment_cart_item'),
    path('decrement-item/<int:item_id>/', views.decrement_cart_item, name='decrement_cart_item'),
    path('toggle-notification/<int:product_id>/', views.toggle_stock_notification, name='toggle_stock_notification'),
    path('toggle-wishlist/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('order-history/', views.order_history, name='order_history'),
    path('order-detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('request-cancellation/<int:order_id>/', views.request_cancellation, name='request_cancellation'),
    path('request-return/<int:order_id>/', views.request_return, name='request_return'),
    path('profile/', views.profile, name='profile'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    path('delete-review/<int:review_id>/', views.delete_review, name='delete_review'),
    path('check_delivery/', views.check_delivery, name='check_delivery'),
    path('toggle-price-notification/<int:product_id>/', views.toggle_price_notification, name='toggle_price_notification'),
    path('password-reset/', 
             auth_views.PasswordResetView.as_view(template_name='store/password_reset_form.html'), 
             name='password_reset'),
    
    path('password-reset/done/', 
             auth_views.PasswordResetDoneView.as_view(template_name='store/password_reset_done.html'), 
             name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', 
             auth_views.PasswordResetConfirmView.as_view(template_name='store/password_reset_confirm.html'), 
             name='password_reset_confirm'),

    path('password-reset-complete/', 
             auth_views.PasswordResetCompleteView.as_view(template_name='store/password_reset_complete.html'), 
             name='password_reset_complete'),
]