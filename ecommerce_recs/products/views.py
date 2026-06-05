import os
import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from .models import Product, Category, Cart, CartItem, Wishlist, Order, OrderItem
from recommendation.models import PurchaseHistory, UserRating
from recommendation.engine.serving import record_product_view, get_trending_products, record_search
from recommendation.engine.content_based import ContentBasedFilter


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def catalog(request):
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()

    products = Product.objects.filter(is_active=True)
    current_category_obj = None

    # ── MODE 1: Category click ──────────────────────────────────────────
    # User clicked a category link. Filter strictly to that category.
    # Diversity booster does NOT run. Only items in this category are shown.
    if category_slug:
        lookup_slug = category_slug
        if category_slug == 'other-electronics':
            lookup_slug = 'accessories-other'

        current_category_obj = Category.objects.filter(slug=lookup_slug).first()
        if current_category_obj:
            products = products.filter(category=current_category_obj)

    # ── Price filter (applies to both modes) ────────────────────────────
    original_query = query
    semantic_query = query  # may have price stripped out
    if query:
        import re
        price_match = re.search(
            r'(?:under|in|below|less than|<)\s*\$?\s*(\d+(?:\.\d{2})?)\s*\$?|(\d+(?:\.\d{2})?)\s*\$',
            query.lower()
        )
        if price_match:
            max_price = price_match.group(1) or price_match.group(2)
            if max_price:
                products = products.filter(price__lte=Decimal(max_price))
                # Strip the price part so semantic search focuses on the product type
                semantic_query = re.sub(
                    r'(?:under|in|below|less than|<)\s*\$?\s*\d+(?:\.\d{2})?\s*\$?|\d+(?:\.\d{2})?\s*\$',
                    '', query.lower()
                ).strip()

    # ── MODE 2: Search query ────────────────────────────────────────────
    # User typed something in the search bar.
    if semantic_query:

        cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
        search_asins = []
        if os.path.exists(cbf_path):
            try:
                cbf = ContentBasedFilter.load(cbf_path)
                # Get top 200 semantic matches; query expansion happens inside this method
                recs = cbf.get_recommendations_from_text(semantic_query, n=200)
                # Filter out weak matches (e.g. from single synonym match)
                search_asins = [asin for asin, score in recs if score > 0.05]
            except Exception:
                pass

        applied_semantic = False
        if search_asins:
            from django.db.models import Case, When
            preserved = Case(*[When(asin=asin, then=pos) for pos, asin in enumerate(search_asins)])
            semantic_products = products.filter(asin__in=search_asins).order_by(preserved)
            if semantic_products.exists():
                products = semantic_products
                applied_semantic = True

        # Fallback: plain text search if semantic returned nothing
        if not applied_semantic:
            from django.db.models import Q
            products = products.filter(
                Q(title__icontains=semantic_query) |
                Q(description__icontains=semantic_query) |
                Q(brand__icontains=semantic_query) |
                Q(category__name__icontains=semantic_query)
            )

    # Record search for analytics
    if original_query:
        if not request.session.session_key:
            request.session.create()
        record_search(request.user, original_query, request.session.session_key)

    product_list = list(products)

    # ── Hero boosting (Category mode only) ──────────────────────────────
    # When a category is clicked, bubble the most relevant items to the top.
    if current_category_obj and not semantic_query and product_list:
        category_name = current_category_obj.name
        hero_keywords = [category_name.rstrip('s').lower()]
        if 'Laptop'    in category_name: hero_keywords.extend(['laptop', 'notebook', 'macbook', 'chromebook'])
        if 'Camera'    in category_name: hero_keywords.extend(['camera', 'dslr', 'mirrorless', 'lens'])
        if 'Phone'     in category_name: hero_keywords.extend(['phone', 'iphone', 'galaxy', 'pixel', 'smartphone'])
        if 'Gaming'    in category_name: hero_keywords.extend(['console', 'controller', 'xbox', 'playstation', 'nintendo', 'switch', 'ps5'])
        if 'Printer'   in category_name: hero_keywords.extend(['printer', 'scanner', 'ink', 'toner'])
        if 'Charger'   in category_name: hero_keywords.extend(['charger', 'charging', 'cable', 'usb', 'adapter'])
        if 'Wearable'  in category_name: hero_keywords.extend(['watch', 'fitbit', 'garmin', 'tracker', 'band'])
        if 'Headphone' in category_name: hero_keywords.extend(['headphone', 'earbuds', 'earphone', 'airpods', 'headset'])
        if 'Speaker'   in category_name: hero_keywords.extend(['speaker', 'soundbar', 'subwoofer', 'boombox'])
        if 'Storage'   in category_name: hero_keywords.extend(['ssd', 'hdd', 'drive', 'memory card', 'flash'])
        if 'TV'        in category_name: hero_keywords.extend(['tv', 'television', 'monitor', 'display', 'screen'])
        if 'Network'   in category_name: hero_keywords.extend(['router', 'ethernet', 'wifi', 'switch', 'modem'])
        if 'Smart'     in category_name: hero_keywords.extend(['smart', 'alexa', 'echo', 'ring', 'nest'])
        if 'Power'     in category_name: hero_keywords.extend(['battery', 'power bank', 'surge', 'ups'])

        def is_hero(p):
            title_lower = p.title.lower()
            return any(kw in title_lower for kw in hero_keywords)

        hero_products  = [p for p in product_list if is_hero(p)]
        other_products = [p for p in product_list if not is_hero(p)]
        product_list   = hero_products + other_products



    categories = Category.objects.all()

    paginator = Paginator(product_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': original_query,
        'current_category': category_slug,
    }
    return render(request, 'products/catalog.html', context)


# ---------------------------------------------------------------------------
# Product Detail
# ---------------------------------------------------------------------------

def detail(request, asin):
    product = get_object_or_404(Product, asin=asin, is_active=True)

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    record_product_view(request.user if request.user.is_authenticated else None, product, session_key)

    cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
    similar_products = []
    if os.path.exists(cbf_path):
        cbf = ContentBasedFilter.load(cbf_path)
        sim_recs = cbf.get_similar(asin, n=5)
        for sim_asin, _ in sim_recs:
            try:
                similar_products.append(Product.objects.get(asin=sim_asin))
            except Product.DoesNotExist:
                continue

    reviews = product.ratings.exclude(review_text__isnull=True).exclude(review_text__exact='').order_by('-created_at')[:10]

    context = {
        'product': product,
        'similar_products': similar_products,
        'reviews': reviews,
    }
    return render(request, 'products/detail.html', context)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@login_required
def add_to_cart(request, asin):
    if request.method == 'POST':
        product = get_object_or_404(Product, asin=asin, is_active=True)
        cart, _ = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        messages.success(request, f"Added {product.title[:40]}… to your cart.")
    return redirect('products:detail', asin=asin)


@login_required
def remove_from_cart(request, item_id):
    """Remove a single cart item. Supports AJAX (returns JSON) and standard form POST."""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()

        # Recalculate totals
        cart, _ = Cart.objects.get_or_create(user=request.user)
        new_total = float(cart.total_price)
        item_count = cart.items.count()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'new_total': f'{new_total:.2f}',
                'item_count': item_count,
            })
        messages.success(request, 'Item removed from cart.')
    return redirect('products:cart')


@login_required
def update_cart_quantity(request, item_id):
    """Update cart item quantity. Supports AJAX."""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action', '')

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                cart_item = None

        cart, _ = Cart.objects.get_or_create(user=request.user)
        new_total = float(cart.total_price)
        item_count = cart.items.count()
        item_total = float(cart_item.total_price) if cart_item else 0

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'new_quantity': cart_item.quantity if cart_item else 0,
                'item_total': f'{item_total:.2f}',
                'new_total': f'{new_total:.2f}',
                'item_count': item_count,
            })

    return redirect('products:cart')


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'products/cart.html', {'cart': cart})


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

@login_required
def view_wishlist(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'products/wishlist.html', {'wishlist': wishlist})


def wishlist_toggle(request, asin):
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'unauthenticated',
            'login_url': f"{settings.LOGIN_URL}?next=/products/{asin}/",
        }, status=401)

    if request.method == 'POST':
        product = get_object_or_404(Product, asin=asin, is_active=True)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

        if product in wishlist.products.all():
            wishlist.products.remove(product)
            action = 'removed'
            message = f"Removed '{product.title[:40]}…' from Saved Items."
        else:
            wishlist.products.add(product)
            action = 'added'
            message = f"Saved '{product.title[:40]}…' to Saved Items."

        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'wishlist_count': wishlist.products.count(),
        })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)


# ---------------------------------------------------------------------------
# Checkout — Multi-Step
# ---------------------------------------------------------------------------

SHIPPING_COSTS = {
    'standard': Decimal('0.00'),
    'express': Decimal('9.99'),
    'overnight': Decimal('19.99'),
}
TAX_RATE = Decimal('0.08')  # 8%


@login_required
def checkout_page(request):
    """Render the multi-step checkout form."""
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('products:cart')

    subtotal = cart.total_price
    tax = (Decimal(str(subtotal)) * TAX_RATE).quantize(Decimal('0.01'))
    standard_total = Decimal(str(subtotal)) + tax

    context = {
        'cart': cart,
        'subtotal': subtotal,
        'tax': tax,
        'standard_total': standard_total,
        'shipping_costs': SHIPPING_COSTS,
        'user': request.user,
    }
    return render(request, 'products/checkout.html', context)


@login_required
def place_order(request):
    """Handle the final order submission (POST from step 3 of checkout)."""
    if request.method != 'POST':
        return redirect('products:checkout')

    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('products:cart')

    # --- Collect form data ---
    shipping_method = request.POST.get('shipping_method', 'standard')
    shipping_cost = SHIPPING_COSTS.get(shipping_method, Decimal('0.00'))
    subtotal = Decimal(str(cart.total_price))
    tax = (subtotal * TAX_RATE).quantize(Decimal('0.01'))
    total = subtotal + shipping_cost + tax

    billing_same = request.POST.get('billing_same', 'on') == 'on'

    order = Order.objects.create(
        user=request.user,
        full_name=request.POST.get('full_name', ''),
        email=request.POST.get('email', request.user.email),
        phone=request.POST.get('phone', ''),
        shipping_address=request.POST.get('shipping_address', ''),
        shipping_city=request.POST.get('shipping_city', ''),
        shipping_state=request.POST.get('shipping_state', ''),
        shipping_zip=request.POST.get('shipping_zip', ''),
        shipping_country=request.POST.get('shipping_country', ''),
        shipping_method=shipping_method,
        billing_same_as_shipping=billing_same,
        billing_address=request.POST.get('billing_address', '') if not billing_same else '',
        billing_city=request.POST.get('billing_city', '') if not billing_same else '',
        billing_state=request.POST.get('billing_state', '') if not billing_same else '',
        billing_zip=request.POST.get('billing_zip', '') if not billing_same else '',
        billing_country=request.POST.get('billing_country', '') if not billing_same else '',
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total,
        status='confirmed',
    )

    # --- Create order items and purchase history ---
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_title=item.product.title,
            product_image=item.product.image_url,
            quantity=item.quantity,
            price=item.product.price or Decimal('0.00'),
        )
        PurchaseHistory.objects.create(
            user=request.user,
            product=item.product,
            quantity=item.quantity,
        )

    # --- Clear cart ---
    cart.items.all().delete()

    return redirect('products:order_confirmation', order_number=order.order_number)


@login_required
def order_confirmation(request, order_number):
    """Show order confirmation page."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'products/order_confirmation.html', {'order': order})


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@login_required
def add_review(request, asin):
    if request.method == 'POST':
        product = get_object_or_404(Product, asin=asin, is_active=True)
        rating_val = float(request.POST.get('rating', 0))
        review_text = request.POST.get('review_text', '').strip()

        if 1.0 <= rating_val <= 5.0:
            UserRating.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={'rating': rating_val, 'review_text': review_text},
            )
            ratings = product.ratings.all()
            if ratings.exists():
                avg = sum(r.rating for r in ratings) / ratings.count()
                product.avg_rating = avg
                product.num_ratings = ratings.count()
                product.save()
            messages.success(request, 'Thank you for your review!')
        else:
            messages.error(request, 'Invalid rating value.')

    return redirect('products:detail', asin=asin)


# ---------------------------------------------------------------------------
# Trending
# ---------------------------------------------------------------------------

def trending(request):
    products = get_trending_products(n=20)
    return render(request, 'products/trending.html', {'products': products})
