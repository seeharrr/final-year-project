from django.contrib import admin
from .models import Recommendation, ModelMetadata, UserRating, BrowsingHistory, PurchaseHistory

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'score', 'cf_score', 'cbf_score', 'source', 'alpha_used', 'generated_at']
    list_filter = ['source']
    search_fields = ['user__username', 'product__title']

@admin.register(ModelMetadata)
class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ['model_type', 'trained_at', 'rmse', 'precision_at_k', 'recall_at_k', 'coverage', 'diversity']
    ordering = ['-trained_at']

@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']

@admin.register(BrowsingHistory)
class BrowsingHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'product', 'viewed_at']
    search_fields = ['user__username', 'session_key', 'product__title']

@admin.register(PurchaseHistory)
class PurchaseHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'purchased_at']
    search_fields = ['user__username', 'product__title']
