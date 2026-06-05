from django.urls import path
from . import views

app_name = 'recommendation'

urlpatterns = [
    path('api/', views.api_recommendations, name='api_recommendations'),
    path('eval-report/', views.eval_report, name='eval_report'),
]
