from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Product
import json
import os

class Command(BaseCommand):
    help = 'Prepares product data into a JSON file for the AI knowledge base.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting to prepare AI knowledge base with new discount details...'))

        products = Product.objects.all()
        all_product_data = []

        for product in products:
            # --- YAHAN SE JAADU SHURU HUA HAI ---
            # Har product ke liye discount percentage nikaalna
            discount_percentage = 0
            # Check karte hain ki old_price hai aur price se zyada hai
            if product.old_price and product.old_price > product.price:
                try:
                    # Discount nikaalne ka formula
                    discount = ((product.old_price - product.price) / product.old_price) * 100
                    discount_percentage = round(discount) # Round figure mein discount
                except (TypeError, ZeroDivisionError):
                    # Agar koi galti ho (jaise old_price 0 ho), toh discount 0 rakho
                    discount_percentage = 0
            
            # Product ki saari nayi jaankari ek jagah ikattha karna
            product_info = {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'highlights': product.highlights,
                'price': str(product.price),
                'market_price': str(product.old_price) if product.old_price else None, # Humne iska naam Market Price rakha
                'discount_percentage': discount_percentage, # Yeh nayi cheez hai
                'stock': product.stock,
                'category': product.category.name if product.category else 'N/A',
            }
            # --- JAADU YAHAN KHATM HUA HAI ---
            all_product_data.append(product_info)
            self.stdout.write(f'Processed: {product.name} (Discount: {discount_percentage}%)')

        # Baaki ka code waisa hi hai, data file banane ke liye
        data_dir = os.path.join(settings.BASE_DIR, 'ai_data')
        os.makedirs(data_dir, exist_ok=True)
        
        file_path = os.path.join(data_dir, 'product_knowledge_base.json')

        with open(file_path, 'w') as f:
            json.dump(all_product_data, f, indent=4)

        self.stdout.write(self.style.SUCCESS(f'Successfully created Super AI knowledge base at: {file_path}'))
