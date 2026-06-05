from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .engine.serving import get_recommendations_for_user
from .models import ModelMetadata

@login_required
def api_recommendations(request):
    recs = get_recommendations_for_user(request.user, n=10)
    data = []
    # If falling back to trending, it returns Product queryset, not Recommendation queryset
    # We must handle both cases
    for r in recs:
        if hasattr(r, 'product'):
            # It's a Recommendation object
            data.append({
                'asin': r.product.asin,
                'title': r.product.title,
                'score': r.score,
                'source': r.source,
                'explanation': r.explanation
            })
        else:
            # It's a trending Product object
            data.append({
                'asin': r.asin,
                'title': r.title,
                'score': 0.0,
                'source': 'trending',
                'explanation': 'Trending product'
            })
            
    return JsonResponse({'recommendations': data})

@staff_member_required
def eval_report(request):
    latest_metadata = ModelMetadata.objects.order_by('-trained_at').first()
    history = ModelMetadata.objects.order_by('-trained_at')[:10]
    
    context = {
        'latest': latest_metadata,
        'history': history,
    }
    return render(request, 'recommendation/eval_report.html', context)

