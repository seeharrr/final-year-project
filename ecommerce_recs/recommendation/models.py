from django.db import models
from django.conf import settings
from products.models import Product

class UserRating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    rating = models.FloatField()
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user} - {self.product} ({self.rating})"

class BrowsingHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='browsing_history')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='viewed_by')
    viewed_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        user_id = self.user if self.user else f"Session {self.session_key}"
        return f"{user_id} viewed {self.product}"

class PurchaseHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchased_by')
    purchased_at = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user} bought {self.quantity} x {self.product}"

class Recommendation(models.Model):
    SOURCE_CHOICES = [
        ('hybrid', 'Hybrid'),
        ('collaborative', 'Collaborative Only'),
        ('content', 'Content-Based Only'),
        ('trending', 'Trending'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recommended_to')
    score = models.FloatField()
    cf_score = models.FloatField(default=0.0)
    cbf_score = models.FloatField(default=0.0)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    explanation = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    alpha_used = models.FloatField(default=0.5)

    class Meta:
        ordering = ['-score']
        unique_together = ('user', 'product')

    def __str__(self):
        return f"Recommendation for {self.user}: {self.product}"

class SearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='search_history')
    query = models.CharField(max_length=255)
    searched_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['-searched_at']
        verbose_name_plural = "Search histories"

    def __str__(self):
        user_id = self.user if self.user else f"Session {self.session_key}"
        return f"{user_id} searched for '{self.query}'"

class ModelMetadata(models.Model):
    MODEL_CHOICES = [
        ('svd', 'SVD'),
        ('tfidf', 'TF-IDF'),
    ]

    model_type = models.CharField(max_length=10, choices=MODEL_CHOICES)
    trained_at = models.DateTimeField(auto_now_add=True)
    rmse = models.FloatField(null=True, blank=True)
    precision_at_k = models.FloatField(null=True, blank=True)
    recall_at_k = models.FloatField(null=True, blank=True)
    coverage = models.FloatField(null=True, blank=True)
    diversity = models.FloatField(null=True, blank=True)
    k_value = models.IntegerField(default=10)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.model_type} trained at {self.trained_at}"
