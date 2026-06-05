from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'asin', 'brand', 'category', 'avg_rating', 'num_ratings', 'is_active']
    list_filter = ['category', 'is_active', 'brand']
    search_fields = ['title', 'asin', 'brand']
    list_editable = ['is_active']
