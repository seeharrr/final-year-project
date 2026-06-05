import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from products.models import Product
from recommendation.models import Recommendation, BrowsingHistory, PurchaseHistory, UserRating
from recommendation.engine.collaborative import CollaborativeFilter
from recommendation.engine.content_based import ContentBasedFilter
from recommendation.engine.hybrid import HybridRecommender

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate recommendations for users'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='Generate for specific user ID')
        parser.add_argument('--all', action='store_true', help='Generate for all active users')

    def handle(self, *args, **options):
        if not options['user_id'] and not options['all']:
            self.stdout.write(self.style.ERROR("Must provide --user-id or --all"))
            return
            
        cf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cf_model.joblib')
        cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
        
        if not os.path.exists(cf_path) or not os.path.exists(cbf_path):
            self.stdout.write(self.style.ERROR("Models not found. Run train_models first."))
            return
            
        cf = CollaborativeFilter.load(cf_path)
        cbf = ContentBasedFilter.load(cbf_path)
        hybrid = HybridRecommender(cf, cbf)
        
        users = []
        if options['all']:
            users = User.objects.filter(is_active=True)
        else:
            try:
                users = [User.objects.get(id=options['user_id'])]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User {options['user_id']} not found"))
                return
                
        all_product_asins = list(Product.objects.filter(is_active=True).values_list('asin', flat=True))
        
        count = 0
        for user in users:
            # 3a. Rated products (CF)
            user_ratings_count = UserRating.objects.filter(user=user).count()
            
            # 3b. Browsed (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            viewed_asins = list(BrowsingHistory.objects.filter(
                user=user, viewed_at__gte=thirty_days_ago
            ).values_list('product__asin', flat=True))
            
            # 3c. Purchased
            purchased_asins = list(PurchaseHistory.objects.filter(
                user=user
            ).values_list('product__asin', flat=True))
            
            # 3d. Search History (last 30 days)
            search_queries = list(SearchHistory.objects.filter(
                user=user, searched_at__gte=thirty_days_ago
            ).values_list('query', flat=True)[:10])
            
            # 3e. Ratings
            rated_asins = list(UserRating.objects.filter(user=user).values_list('product__asin', 'rating'))
            
            if user_ratings_count == 0 and not viewed_asins and not purchased_asins and not search_queries:
                continue # Nothing to base recommendations on
                
            if user_ratings_count == 0 and (viewed_asins or search_queries):
                # We can use the hybrid recommend method with alpha=0 or specifically cold start
                # but better to use the enhanced recommend logic
                recs = hybrid.recommend(
                    user_id=str(user.id),
                    user_django_id=user.id,
                    viewed_asins=viewed_asins,
                    purchased_asins=purchased_asins,
                    all_product_ids=all_product_asins,
                    n=10,
                    user_rating_count=0,
                    rated_asins=rated_asins,
                    search_queries=search_queries
                )
            else:
                recs = hybrid.recommend(
                    user_id=str(user.id),
                    user_django_id=user.id,
                    viewed_asins=viewed_asins,
                    purchased_asins=purchased_asins,
                    all_product_ids=all_product_asins,
                    n=10,
                    user_rating_count=user_ratings_count,
                    rated_asins=rated_asins,
                    search_queries=search_queries
                )
                
            # Upsert
            for rec in recs:
                try:
                    product = Product.objects.get(asin=rec['asin'])
                    Recommendation.objects.update_or_create(
                        user=user,
                        product=product,
                        defaults={
                            'score': rec['hybrid_score'],
                            'cf_score': rec['cf_score'],
                            'cbf_score': rec['cbf_score'],
                            'alpha_used': rec['alpha'],
                            'source': rec['source'],
                            'explanation': rec['explanation']
                        }
                    )
                except Product.DoesNotExist:
                    continue
                    
            count += 1
            if count % 100 == 0:
                self.stdout.write(f"Processed {count} users...")
                
        self.stdout.write(self.style.SUCCESS(f"Finished generating recommendations for {count} users."))
