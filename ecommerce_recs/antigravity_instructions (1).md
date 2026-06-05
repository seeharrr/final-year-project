# Antigravity Agent Instructions
## AI-Based Recommendation System for E-Commerce Platform

---

## HOW TO USE THESE INSTRUCTIONS

These instructions are structured for Google Antigravity's Agent Manager.
Use **Plan Mode** for each phase before execution. Set **Artifact Review Policy**
to "Asks for Review" so you can verify each phase before proceeding.
Use **Agent-Assisted Development** mode (recommended) throughout.

Paste each PHASE PROMPT into a new Agent Manager task in sequence.
Do not start Phase N+1 until Phase N artifacts have been reviewed and approved.

---

## MASTER PROJECT BRIEF
*(Paste this into Agent Manager → Knowledge Base so all agents have global context)*

```
Project: AI-Based E-Commerce Recommendation System
Language: Python 3.11+
Framework: Django 4.2
Frontend: Django Templates + Bootstrap 5
Database: SQLite (default Django DB)
ML Libraries: scikit-learn, scikit-surprise, pandas, numpy
Viz: matplotlib, seaborn
Dataset: Amazon Electronics dataset (Kaggle)

Core Goal:
Build a hybrid recommendation engine combining:
  1. Collaborative Filtering — Surprise SVD on user-item rating matrix
  2. Content-Based Filtering — TF-IDF + Cosine Similarity on product metadata
  3. Hybrid Score Combiner — dynamic weighted blend: α = min(1.0, num_ratings / 20)
     (new users lean content-based; active users lean collaborative)

Key Design Decisions:
- Models are PRECOMPUTED (batch, nightly), serialized via joblib, NOT run per-request
- Top-N recommendations per user stored in DB after model inference
- Cold-start users (0 ratings) get purely content-based recommendations
- Anonymous (not logged-in) users get session-based content-based recommendations
- Evaluation metrics: RMSE (collaborative), Precision@K, Recall@K, Coverage, Diversity
- "Why this recommendation?" explanation stored alongside each recommendation record

Data Preprocessing Rules:
- Filter out users with fewer than 5 ratings
- Filter out products with fewer than 10 ratings
- These filters applied BEFORE any model training

Architecture Layers:
  Frontend  → Django Templates + Bootstrap 5
  Backend   → Django views, models, REST-ish URLs
  Engine    → recommendation/engine/ (training + serving modules)
  Data      → SQLite + precomputed model files (models/saved/)
  Eval      → recommendation/evaluation/ (metrics + chart generation)
```

---

## PHASE 1 — Project Scaffolding & Django Setup

**Agent Manager Task Title:** `Phase 1 — Django project scaffold`
**Suggested Mode:** Plan Mode → review plan → execute

```
TASK: Scaffold the full Django project structure for the AI recommendation system.

Create the following directory and file layout:

ecommerce_recs/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── ecommerce_recs/           ← Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── users/                    ← Custom user auth app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── templates/users/
│       ├── login.html
│       ├── register.html
│       └── profile.html
├── products/                 ← Product catalog app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── templates/products/
│       ├── catalog.html
│       ├── detail.html
│       └── trending.html
├── recommendation/           ← Recommendation engine app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── collaborative.py
│   │   ├── content_based.py
│   │   ├── hybrid.py
│   │   └── serving.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   └── charts.py
│   ├── management/
│   │   └── commands/
│   │       ├── train_models.py
│   │       └── generate_recommendations.py
│   └── templates/recommendation/
│       ├── dashboard.html
│       └── eval_report.html
├── dashboard/                ← Main user-facing dashboard app
│   ├── views.py
│   ├── urls.py
│   └── templates/dashboard/
│       └── index.html
├── static/
│   ├── css/
│   │   └── main.css
│   └── js/
│       └── main.js
└── models/
    └── saved/                ← joblib-serialized model files go here
        └── .gitkeep

REQUIREMENTS FILE must include:
django==4.2.*
scikit-learn>=1.3
scikit-surprise>=1.1
pandas>=2.0
numpy>=1.24
joblib>=1.3
matplotlib>=3.7
seaborn>=0.12
python-dotenv>=1.0
Pillow>=10.0

SETTINGS.py requirements:
- Use python-dotenv for SECRET_KEY and DEBUG
- Configure INSTALLED_APPS with all four apps: users, products, recommendation, dashboard
- Configure STATIC_ROOT and STATICFILES_DIRS
- Set AUTH_USER_MODEL = 'users.CustomUser'
- Set LOGIN_URL, LOGIN_REDIRECT_URL, LOGOUT_REDIRECT_URL

After scaffolding, run:
  python manage.py check
to verify no configuration errors. Produce a Plan Artifact listing all files
created before executing.
```

---

## PHASE 2 — Django Models

**Agent Manager Task Title:** `Phase 2 — Database models`
**Suggested Mode:** Plan Mode → review → execute

```
TASK: Implement all Django models for the recommendation system.

=== users/models.py ===
CustomUser(AbstractUser):
  - bio: TextField (blank=True)
  - avatar: ImageField (optional)
  - date_of_birth: DateField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add=True)

=== products/models.py ===
Category(Model):
  - name: CharField(max_length=100, unique=True)
  - slug: SlugField(unique=True)

Product(Model):
  - asin: CharField(max_length=20, unique=True)  ← Amazon product ID
  - title: CharField(max_length=500)
  - description: TextField(blank=True)
  - price: DecimalField(max_digits=10, decimal_places=2, null=True)
  - category: ForeignKey(Category)
  - brand: CharField(max_length=200, blank=True)
  - avg_rating: FloatField(default=0.0)
  - num_ratings: IntegerField(default=0)
  - image_url: URLField(blank=True)
  - created_at: DateTimeField(auto_now_add=True)
  - is_active: BooleanField(default=True)

  Meta: ordering = ['-num_ratings']
  Property: rating_stars → returns integer 1-5

=== recommendation/models.py ===
UserRating(Model):
  - user: ForeignKey(CustomUser, on_delete=CASCADE)
  - product: ForeignKey(Product, on_delete=CASCADE)
  - rating: FloatField()  ← 1.0 to 5.0
  - created_at: DateTimeField(auto_now_add=True)
  Meta: unique_together = ('user', 'product')

BrowsingHistory(Model):
  - user: ForeignKey(CustomUser, on_delete=CASCADE)
  - product: ForeignKey(Product, on_delete=CASCADE)
  - viewed_at: DateTimeField(auto_now_add=True)
  - session_key: CharField(max_length=40, blank=True)  ← for anonymous users
  Meta: ordering = ['-viewed_at']

PurchaseHistory(Model):
  - user: ForeignKey(CustomUser, on_delete=CASCADE)
  - product: ForeignKey(Product, on_delete=CASCADE)
  - purchased_at: DateTimeField(auto_now_add=True)
  - quantity: PositiveIntegerField(default=1)

Recommendation(Model):
  - user: ForeignKey(CustomUser, on_delete=CASCADE)
  - product: ForeignKey(Product, on_delete=CASCADE)
  - score: FloatField()                ← hybrid score (0.0 to 1.0)
  - cf_score: FloatField(default=0.0)  ← collaborative component
  - cbf_score: FloatField(default=0.0) ← content-based component
  - source: CharField(choices=[
        ('hybrid', 'Hybrid'),
        ('collaborative', 'Collaborative Only'),
        ('content', 'Content-Based Only'),
        ('trending', 'Trending'),
    ])
  - explanation: TextField(blank=True)  ← "Because you viewed X" string
  - generated_at: DateTimeField(auto_now_add=True)
  - alpha_used: FloatField(default=0.5) ← the α value used at generation time
  Meta: ordering = ['-score']
        unique_together = ('user', 'product')

ModelMetadata(Model):
  - model_type: CharField(choices=[('svd','SVD'),('tfidf','TF-IDF')])
  - trained_at: DateTimeField(auto_now_add=True)
  - rmse: FloatField(null=True)
  - precision_at_k: FloatField(null=True)
  - recall_at_k: FloatField(null=True)
  - coverage: FloatField(null=True)
  - diversity: FloatField(null=True)
  - k_value: IntegerField(default=10)
  - notes: TextField(blank=True)

After creating models:
1. Run makemigrations and migrate
2. Register all models in their respective admin.py files with list_display configured
3. Create a superuser with username=admin, password=admin123 for development
```

---

## PHASE 3 — Data Preprocessing Pipeline

**Agent Manager Task Title:** `Phase 3 — Data preprocessing`
**Suggested Mode:** Agent-Assisted

```
TASK: Build the data preprocessing pipeline for the Amazon Electronics dataset.

Create: recommendation/engine/preprocessing.py

This module must provide:

1. load_amazon_dataset(filepath: str) -> pd.DataFrame
   - Load CSV/JSON from filepath
   - Expected columns: reviewerID, asin, overall (rating), reviewText, summary
   - Drop rows where overall, reviewerID, or asin is null
   - Convert 'overall' to float
   - Return cleaned DataFrame

2. filter_sparse_data(df: pd.DataFrame, min_user_ratings=5, min_product_ratings=10) -> pd.DataFrame
   - Remove users with fewer than min_user_ratings ratings
   - Remove products with fewer than min_product_ratings ratings
   - Apply iteratively until stable (some users/products may become sparse after removal)
   - Log how many users and products were removed
   - Return filtered DataFrame

3. build_user_item_matrix(df: pd.DataFrame) -> pd.DataFrame
   - Pivot table: rows=reviewerID, columns=asin, values=overall
   - Fill NaN with 0
   - Return matrix

4. build_product_feature_text(products_df: pd.DataFrame) -> pd.Series
   - Combine title + brand + category + description into one string per product
   - Clean text: lowercase, remove special characters
   - Return Series indexed by asin

5. encode_users_products(df: pd.DataFrame) -> tuple[dict, dict, dict, dict]
   - Return: user_to_idx, idx_to_user, product_to_idx, idx_to_product
   - These integer mappings are needed by Surprise

6. prepare_surprise_dataset(df: pd.DataFrame) -> surprise.Dataset
   - Use surprise.Reader with rating_scale=(1, 5)
   - Load from pandas DataFrame
   - Return surprise Dataset object

Also create: recommendation/engine/data_loader.py
   - load_products_to_db(filepath: str)
     Reads the Amazon dataset and bulk-creates Product objects in Django DB
     Maps: asin, title (from 'title' column), avg_rating (from computed mean)
     Use Product.objects.bulk_create() with batch_size=500, ignore_conflicts=True

Write unit tests in recommendation/tests/test_preprocessing.py using
small synthetic DataFrames (5 users, 10 products) to verify all functions.
```

---

## PHASE 4 — Recommendation Engine (Core ML)

**Agent Manager Task Title:** `Phase 4 — ML engine implementation`
**Suggested Mode:** Plan Mode → review plan → execute

```
TASK: Implement the three recommendation engine modules.

=== recommendation/engine/collaborative.py ===

class CollaborativeFilter:

  __init__(self, n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
    Store hyperparameters.

  train(self, surprise_dataset) -> dict
    - Use surprise.SVD with stored hyperparameters
    - Perform 5-fold cross-validation using surprise.cross_validate
    - Fit final model on full training set
    - Store model as self.model
    - Return dict: {rmse_mean, rmse_std, mae_mean}

  predict(self, user_id: str, product_id: str) -> float
    - Return predicted rating (1.0–5.0) using self.model.predict()
    - Return 0.0 if user or product not in training data

  get_top_n(self, user_id: str, all_product_ids: list, n=20) -> list[tuple]
    - Predict rating for all products user has NOT yet rated
    - Return top-n as list of (product_id, predicted_score) sorted descending

  save(self, path: str)
    - joblib.dump({'model': self.model, 'trained_at': datetime.now()}, path)

  @classmethod
  load(cls, path: str) -> 'CollaborativeFilter'
    - Load joblib file, restore model, return instance


=== recommendation/engine/content_based.py ===

class ContentBasedFilter:

  __init__(self, max_features=5000)
    Store max_features.

  fit(self, product_texts: pd.Series)
    - product_texts: Series indexed by asin, values are combined text strings
    - Fit TfidfVectorizer(max_features=max_features, stop_words='english')
    - Compute TF-IDF matrix
    - Store vectorizer, matrix, and index (asin list) as instance attributes

  get_similar(self, asin: str, n=20) -> list[tuple]
    - Compute cosine similarity between target product and all others
    - Return top-n most similar as list of (asin, similarity_score), excluding self
    - Return empty list if asin not in index

  get_user_profile_recommendations(self, viewed_asins: list, purchased_asins: list, n=20) -> list[tuple]
    - Build user content profile: mean TF-IDF vector of viewed + purchased products
      (weight purchased products 2x relative to viewed)
    - Compute cosine similarity of profile against all products
    - Return top-n as list of (asin, score)

  save(self, path: str)
    - joblib.dump({'vectorizer': self.vectorizer, 'matrix': self.matrix,
                   'index': self.index, 'trained_at': datetime.now()}, path)

  @classmethod
  load(cls, path: str) -> 'ContentBasedFilter'


=== recommendation/engine/hybrid.py ===

class HybridRecommender:

  __init__(self, cf: CollaborativeFilter, cbf: ContentBasedFilter)
    Store both engines.

  compute_alpha(self, num_ratings: int) -> float
    """Dynamic weight for collaborative filtering."""
    return min(1.0, num_ratings / 20)

  recommend(self, user_id: str, user_django_id: int,
            viewed_asins: list, purchased_asins: list,
            all_product_ids: list, n=10) -> list[dict]
    """
    Returns top-n recommendations as list of dicts:
    {
      asin: str,
      hybrid_score: float,
      cf_score: float,
      cbf_score: float,
      alpha: float,
      source: str,          ← 'hybrid', 'content', or 'collaborative'
      explanation: str
    }

    Algorithm:
    1. Count user ratings from DB to determine alpha
    2. Get CF top-20: cf.get_top_n(user_id, all_product_ids, n=20)
    3. Get CBF top-20: cbf.get_user_profile_recommendations(viewed_asins, purchased_asins, n=20)
    4. Normalize both score lists to [0, 1] using min-max scaling
    5. Merge by asin: hybrid_score = alpha * cf_score_norm + (1-alpha) * cbf_score_norm
    6. Sort by hybrid_score descending, return top-n
    7. Build explanation string:
       - If alpha < 0.3: "Based on products you browsed"
       - If alpha > 0.7: "Users like you also bought this"
       - Else: "Recommended based on your history and similar users"
    """

  recommend_cold_start(self, viewed_asins: list, n=10) -> list[dict]
    """For anonymous / zero-rating users. Pure content-based only."""
    results = self.cbf.get_user_profile_recommendations(viewed_asins, [], n=n)
    return [{'asin': a, 'hybrid_score': s, 'cf_score': 0.0,
             'cbf_score': s, 'alpha': 0.0, 'source': 'content',
             'explanation': 'Based on products you recently viewed'}
            for a, s in results]
```

---

## PHASE 5 — Training & Serving Commands

**Agent Manager Task Title:** `Phase 5 — Management commands & serving layer`
**Suggested Mode:** Agent-Assisted

```
TASK: Implement Django management commands and the serving layer.

=== recommendation/management/commands/train_models.py ===
Management command: python manage.py train_models --dataset-path <path>

Steps:
1. Load and preprocess dataset using preprocessing.py functions
2. Train CollaborativeFilter on Surprise dataset → save to models/saved/cf_model.joblib
3. Fit ContentBasedFilter on product texts → save to models/saved/cbf_model.joblib
4. Run evaluation (see Phase 6) and save ModelMetadata record to DB
5. Print training summary to stdout

=== recommendation/management/commands/generate_recommendations.py ===
Management command: python manage.py generate_recommendations [--user-id <id>] [--all]

Steps:
1. Load both saved models from models/saved/
2. If --all: iterate over all active CustomUser objects
3. For each user:
   a. Fetch user's rated product ASINs (for CF)
   b. Fetch user's browsed ASINs (last 30 days) from BrowsingHistory
   c. Fetch user's purchased ASINs from PurchaseHistory
   d. Call HybridRecommender.recommend()
   e. Bulk-upsert Recommendation objects (update_or_create by user+product)
4. Print progress every 100 users

=== recommendation/engine/serving.py ===

def get_recommendations_for_user(user, n=10) -> QuerySet:
    """
    Primary serving function — called by views.
    Returns Recommendation QuerySet for user, ordered by score desc.
    Falls back to trending products if no recommendations exist.
    """
    recs = Recommendation.objects.filter(user=user).select_related('product').order_by('-score')[:n]
    if recs.count() == 0:
        return get_trending_products(n)
    return recs

def get_trending_products(n=10) -> QuerySet:
    """Returns top-n products by num_ratings as a fallback."""
    return Product.objects.filter(is_active=True).order_by('-num_ratings')[:n]

def get_session_recommendations(session_key: str, n=10) -> list:
    """
    For anonymous users. Reads BrowsingHistory by session_key,
    loads CBF model, returns content-based recommendations.
    Caches result in Django's session framework for 1 hour.
    """

def record_product_view(user_or_none, product, session_key: str):
    """
    Records a product view in BrowsingHistory.
    Works for both authenticated users and anonymous sessions.
    """
```

---

## PHASE 6 — Evaluation Module

**Agent Manager Task Title:** `Phase 6 — Evaluation metrics & charts`
**Suggested Mode:** Agent-Assisted

```
TASK: Build the evaluation and visualisation module.

=== recommendation/evaluation/metrics.py ===

def compute_rmse(model, testset) -> float:
    """Compute RMSE on Surprise testset."""

def precision_at_k(recommended: list, relevant: list, k: int) -> float:
    """
    recommended: list of product ASINs in ranked order
    relevant: list of product ASINs the user actually interacted with
    Returns proportion of top-k recommended items that are relevant.
    """

def recall_at_k(recommended: list, relevant: list, k: int) -> float:
    """
    Returns proportion of relevant items found in top-k recommendations.
    """

def coverage(all_recommendations: dict, catalog_size: int) -> float:
    """
    all_recommendations: {user_id: [asin, ...]} dict
    Returns fraction of catalog that appears in at least one recommendation list.
    """

def diversity(all_recommendations: dict, cbf: ContentBasedFilter) -> float:
    """
    For each user's list, compute mean pairwise (1 - cosine_similarity) between recommended items.
    Average across all users.
    High diversity = varied recommendations.
    """

def run_full_evaluation(cf_model, cbf_model, testset, all_recs, catalog_size) -> dict:
    """
    Run all metrics and return results dict:
    {rmse, precision_at_10, recall_at_10, coverage, diversity}
    """

=== recommendation/evaluation/charts.py ===

def plot_rmse_history(metadata_queryset, output_path: str):
    """Line chart of RMSE over successive training runs. Save as PNG."""

def plot_precision_recall(precision_vals: list, recall_vals: list, k_vals: list, output_path: str):
    """Precision and Recall vs K line chart. Save as PNG."""

def plot_recommendation_score_distribution(scores: list, output_path: str):
    """Histogram of hybrid scores across all recommendations. Save as PNG."""

def plot_coverage_diversity(coverage: float, diversity: float, output_path: str):
    """Simple bar chart comparing coverage and diversity. Save as PNG."""

All charts must use seaborn style, figure size (10, 6), and save to the given path.
Charts are displayed in the admin eval_report.html template.
```

---

## PHASE 7 — Views, URLs & Templates

**Agent Manager Task Title:** `Phase 7 — Frontend views and templates`
**Suggested Mode:** Plan Mode → review → execute

```
TASK: Implement all Django views, URL routing, and Bootstrap 5 templates.

=== URL Structure ===
/                       → dashboard/index.html (requires login)
/products/              → products/catalog.html
/products/<asin>/       → products/detail.html (records BrowsingHistory on GET)
/products/trending/     → products/trending.html
/accounts/login/        → users/login.html
/accounts/register/     → users/register.html
/accounts/profile/      → users/profile.html
/recommendations/api/   → JSON endpoint returning user's top-10 recs
/admin/eval-report/     → recommendation/eval_report.html (staff only)

=== dashboard/views.py — index view ===
@login_required
def index(request):
    - Fetch top-10 recommendations via serving.get_recommendations_for_user(request.user)
    - Fetch top-5 trending products via serving.get_trending_products(5)
    - Fetch user's last 5 browsing history items
    - Pass all to template context

=== products/views.py — detail view ===
def detail(request, asin):
    - Get Product by asin or 404
    - Call serving.record_product_view(request.user or None, product, session_key)
    - Fetch similar products via CBF: get top-5 similar ASINs
    - Render template with product, similar_products

=== Template design requirements (Bootstrap 5) ===

base.html:
  - Navbar: brand name, links (Home, Catalog, Trending), user auth state
  - Flash messages block
  - Main content block
  - Footer with project info

dashboard/index.html:
  - Hero greeting: "Welcome back, {username}"
  - Section: "Recommended for you" — horizontal scroll card row
    Each card: product image (or placeholder), title (truncated 50 chars),
    avg_rating (★ stars), explanation text (italicised, muted), "View" button
  - Section: "Trending now" — 5-product grid
  - Section: "Recently viewed" — last 5 browsed products

products/detail.html:
  - Product image (left), title + description + price + rating (right)
  - "Why recommended?" badge if product is in user's recommendations
  - Similar products section: 5 cards in a row

products/catalog.html:
  - Search bar (GET parameter q, filters by title icontains)
  - Category filter sidebar
  - Product grid: 3 columns, paginated (12 per page)

All templates: mobile-responsive, clean Bootstrap 5 grid, no inline styles.
Use Bootstrap card component for product cards consistently.
```

---

## PHASE 8 — Admin Panel & Eval Report

**Agent Manager Task Title:** `Phase 8 — Admin configuration and eval dashboard`
**Suggested Mode:** Agent-Assisted

```
TASK: Configure Django admin and build the evaluation report page.

=== Admin registrations ===

products/admin.py:
  @admin.register(Product)
  class ProductAdmin(ModelAdmin):
    list_display = ['title', 'asin', 'brand', 'category', 'avg_rating', 'num_ratings', 'is_active']
    list_filter = ['category', 'is_active', 'brand']
    search_fields = ['title', 'asin', 'brand']
    list_editable = ['is_active']

recommendation/admin.py:
  @admin.register(Recommendation)
  class RecommendationAdmin(ModelAdmin):
    list_display = ['user', 'product', 'score', 'cf_score', 'cbf_score', 'source', 'alpha_used', 'generated_at']
    list_filter = ['source']
    search_fields = ['user__username', 'product__title']

  @admin.register(ModelMetadata)
  class ModelMetadataAdmin(ModelAdmin):
    list_display = ['model_type', 'trained_at', 'rmse', 'precision_at_k', 'recall_at_k', 'coverage', 'diversity']
    ordering = ['-trained_at']

  @admin.register(UserRating)
  class UserRatingAdmin(ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']

=== Eval Report page ===

URL: /recommendations/eval-report/ (staff_member_required)

View fetches:
  - Last 5 ModelMetadata records for chart history
  - Latest record's metric values for the summary cards
  - Paths to pre-generated chart PNGs (stored in static/eval_charts/)

Template (recommendation/eval_report.html):
  - Page title: "Model Evaluation Dashboard"
  - Row of 4 metric summary cards: RMSE | Precision@10 | Recall@10 | Coverage
  - Each card: metric name, current value (large, bold), previous value (small, muted), delta indicator (↑/↓)
  - RMSE history chart (line chart PNG embedded as <img>)
  - Precision/Recall vs K chart
  - Score distribution histogram
  - Coverage & Diversity bar chart
  - Table of last 10 ModelMetadata records

Admin site customisation:
  - admin.site.site_header = "RecSys Admin"
  - admin.site.site_title = "RecSys"
  - admin.site.index_title = "Platform Management"
```

---

## PHASE 9 — Testing, Fixtures & Final QA

**Agent Manager Task Title:** `Phase 9 — Tests, seed data, and QA`
**Suggested Mode:** Review-Driven (high caution — touches DB and model files)

```
TASK: Write tests, create seed fixtures, and perform final QA checks.

=== Tests ===

recommendation/tests/test_engine.py:
  - TestCollaborativeFilter: train on tiny synthetic Surprise dataset (5 users, 8 products),
    assert RMSE < 2.0, assert predict() returns float in [1,5]
  - TestContentBasedFilter: fit on 10 synthetic product texts,
    assert get_similar() returns list of tuples, assert self not in results
  - TestHybridRecommender: mock CF and CBF with fixed outputs,
    assert compute_alpha(0) == 0.0, compute_alpha(10) == 0.5, compute_alpha(25) == 1.0
    assert recommend() returns list of dicts with required keys

recommendation/tests/test_metrics.py:
  - Test precision_at_k: known recommended/relevant lists, assert exact values
  - Test recall_at_k: same
  - Test coverage: known recommendations dict, assert float in [0,1]

=== Fixtures (seed data for development) ===

Create: products/fixtures/sample_products.json
  - 20 sample electronics products with realistic titles, brands, ASINs, ratings
  - Include 3 categories: Headphones, Laptops, Smartphones

Create: recommendation/fixtures/sample_users.json
  - 5 sample users (username: user1..user5, password: testpass123)
  - 30 UserRating records distributed across users and products

Load order: python manage.py loaddata sample_products sample_users

=== Final QA checklist (agent must verify each item) ===

1. python manage.py check → exits with no errors
2. python manage.py test recommendation → all tests pass
3. python manage.py runserver → server starts, /admin/ accessible
4. Load fixtures → dashboard loads with recommendations for user1
5. Product detail page records BrowsingHistory on visit
6. Anonymous user visits /products/<asin>/ → session BrowsingHistory recorded
7. /recommendations/api/ returns valid JSON with 10 items for logged-in user
8. Admin eval-report page loads without errors
9. All Bootstrap templates render correctly on mobile viewport (use built-in browser)

Produce a final QA Artifact listing each checklist item as PASS / FAIL with notes.
```

---

## RECOMMENDED ANTIGRAVITY SETTINGS FOR THIS PROJECT

Set these in Antigravity → Settings → Agent before starting:

| Setting | Recommended Value | Reason |
|---|---|---|
| Artifact Review Policy | Asks for Review | Verify each phase plan before execution |
| Terminal Command Policy | Request Review | DB migrations need human confirmation |
| Terminal Sandbox | Enabled | Restrict to workspace only |
| Development Mode | Agent-Assisted | Balance autonomy with oversight |
| Model | Claude Sonnet 4.6 | Best for complex multi-file Python projects |

Use **Plan Mode** for Phases 1, 2, 4, and 7 (high structural complexity).
Use **Agent-Assisted** for Phases 3, 5, 6, 8 (well-defined, lower risk).
Use **Review-Driven** for Phase 9 (tests and seed data, touches production DB).

---

## KNOWLEDGE BASE SNIPPETS
*(Save these in Antigravity's Knowledge Base for agent reference)*

**Hybrid alpha formula:**
```python
alpha = min(1.0, num_ratings / 20)
hybrid_score = alpha * cf_score_normalized + (1 - alpha) * cbf_score_normalized
```

**Model file paths:**
```
models/saved/cf_model.joblib   ← CollaborativeFilter
models/saved/cbf_model.joblib  ← ContentBasedFilter
```

**Training commands:**
```bash
python manage.py train_models --dataset-path data/amazon_electronics.csv
python manage.py generate_recommendations --all
```

**Data filter thresholds:**
- min_user_ratings = 5
- min_product_ratings = 10
- Apply iteratively until stable
