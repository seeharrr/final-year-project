from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from recommendation.engine.serving import get_recommendations_for_user, get_trending_products
from recommendation.models import BrowsingHistory

@login_required
def index(request):
    recs = get_recommendations_for_user(request.user, n=10)
    trending = get_trending_products(n=5)
    
    recent_history = BrowsingHistory.objects.filter(
        user=request.user
    ).select_related('product').order_by('-viewed_at')[:5]
    
    context = {
        'recommendations': recs,
        'trending': trending,
        'recent_history': recent_history
    }
    return render(request, 'dashboard/index.html', context)
