// RecSys main JavaScript

// Helper to get CSRF cookie value for secure AJAX POSTs
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Sleek Custom Micro-Toast Notification System
function showToast(message, isSuccess = true) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = 'shadow-lg border-0 m-0 mb-2 py-3 px-4 d-flex align-items-center';
    toast.style.borderRadius = '1rem';
    toast.style.color = '#fff';
    toast.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px)';
    
    if (isSuccess) {
        toast.style.background = 'linear-gradient(135deg, var(--primary), var(--primary-dark))';
        toast.innerHTML = `<svg class="me-2" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span class="small fw-bold">${message}</span>`;
    } else {
        toast.style.background = 'linear-gradient(135deg, var(--accent), #e11d48)';
        toast.innerHTML = `<svg class="me-2" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><span class="small fw-bold">${message}</span>`;
    }
    
    container.appendChild(toast);
    
    // Smooth Animation Trigger
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 50);
    
    // Auto Dismiss after 3.5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => {
            toast.remove();
        }, 400);
    }, 3500);
}

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss standard bootstrap alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // Wishlist / Saved Items Bookmark Handler
    const wishlistButtons = document.querySelectorAll('.wishlist-btn');
    wishlistButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const asin = this.getAttribute('data-asin');
            if (!asin) return;
            
            const url = `/products/${asin}/wishlist/toggle/`;
            const csrftoken = getCookie('csrftoken');
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => {
                if (response.status === 401) {
                    return response.json().then(data => {
                        window.location.href = data.login_url;
                        throw new Error('Redirecting to login');
                    });
                }
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    const isAdded = (data.action === 'added');
                    
                    // Update all bookmark icon button instances for this product
                    const identicalButtons = document.querySelectorAll(`.wishlist-btn[data-asin="${asin}"]`);
                    identicalButtons.forEach(btn => {
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            if (isAdded) {
                                svg.setAttribute('fill', 'currentColor');
                                svg.classList.add('text-dark');
                            } else {
                                svg.setAttribute('fill', 'none');
                                svg.classList.remove('text-dark');
                            }
                        }
                    });
                    
                    // Live badge update
                    const countBadge = document.getElementById('navbar-wishlist-count');
                    if (countBadge) {
                        countBadge.textContent = data.wishlist_count;
                    }
                    
                    // Display micro-toast
                    showToast(data.message, isAdded);
                    
                    // Dynamic Page Manipulation: If we are on the Wishlist page, animate card deletion!
                    const wishlistItemCard = document.getElementById(`card-${asin}`);
                    if (wishlistItemCard) {
                        wishlistItemCard.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                        wishlistItemCard.style.opacity = '0';
                        wishlistItemCard.style.transform = 'scale(0.85) translateY(15px)';
                        
                        setTimeout(() => {
                            wishlistItemCard.remove();
                            
                            // Check if wishlist grid is empty now
                            const grid = document.getElementById('wishlist-grid');
                            if (grid && grid.querySelectorAll('.wishlist-item-card').length === 0) {
                                const container = document.getElementById('wishlist-container');
                                if (container) {
                                    container.style.opacity = '0';
                                    container.style.transition = 'opacity 0.4s ease';
                                    setTimeout(() => {
                                        container.innerHTML = `
                                            <div class="text-center py-5" id="wishlist-empty-state" style="opacity: 0; transform: translateY(20px); transition: all 0.5s ease;">
                                                <div class="mb-4 text-muted opacity-50">
                                                    <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-bookmark"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
                                                </div>
                                                <h3 class="fw-bold text-dark mb-2">Your Saved Items is empty</h3>
                                                <p class="text-muted mb-4 fs-5">Save products here to keep track of them for later!</p>
                                                <a href="/products/" class="btn btn-primary btn-lg rounded-pill px-5 shadow">Browse Catalog</a>
                                            </div>
                                        `;
                                        container.style.opacity = '1';
                                        const emptyState = document.getElementById('wishlist-empty-state');
                                        setTimeout(() => {
                                            emptyState.style.opacity = '1';
                                            emptyState.style.transform = 'translateY(0)';
                                        }, 50);
                                    }, 400);
                                }
                            }
                        }, 500);
                    }
                }
            })
            .catch(error => {
                if (error.message !== 'Redirecting to login') {
                    console.error('Bookmark error:', error);
                }
            });
        });
    });

    // ===== Cart: Remove item via AJAX =====
    document.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const csrftoken = getCookie('csrftoken');
            const row = document.getElementById('cart-row-' + itemId);

            fetch(`/products/cart/remove/${itemId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    if (row) {
                        row.classList.add('removing');
                        setTimeout(() => row.remove(), 400);
                    }
                    // Update totals
                    ['cart-subtotal', 'cart-total'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.textContent = '$' + data.new_total;
                    });
                    // Update navbar badge
                    const badge = document.querySelector('.nav-link .badge');
                    if (badge) badge.textContent = data.item_count;

                    showToast('Item removed from cart', true);

                    // Show empty state if no items left
                    if (data.item_count === 0) {
                        setTimeout(() => {
                            const container = document.getElementById('cart-items-container');
                            const summary = document.getElementById('cart-summary');
                            const empty = document.getElementById('cart-empty-state');
                            if (container) container.style.display = 'none';
                            if (summary) summary.style.display = 'none';
                            if (empty) empty.style.display = 'block';
                        }, 450);
                    }
                }
            })
            .catch(err => console.error('Remove error:', err));
        });
    });

    // ===== Cart: Update quantity via AJAX =====
    document.querySelectorAll('.qty-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const action = this.dataset.action;
            const csrftoken = getCookie('csrftoken');

            const formData = new FormData();
            formData.append('action', action);

            fetch(`/products/cart/update/${itemId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    if (data.new_quantity === 0) {
                        const row = document.getElementById('cart-row-' + itemId);
                        if (row) { row.classList.add('removing'); setTimeout(() => row.remove(), 400); }
                    } else {
                        const qtyEl = document.getElementById('qty-' + itemId);
                        const totalEl = document.getElementById('item-total-' + itemId);
                        if (qtyEl) qtyEl.textContent = data.new_quantity;
                        if (totalEl) totalEl.textContent = '$' + data.item_total;
                    }
                    ['cart-subtotal', 'cart-total'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.textContent = '$' + data.new_total;
                    });
                    const badge = document.querySelector('.nav-link .badge');
                    if (badge) badge.textContent = data.item_count;

                    if (data.item_count === 0) {
                        setTimeout(() => {
                            const container = document.getElementById('cart-items-container');
                            const summary = document.getElementById('cart-summary');
                            const empty = document.getElementById('cart-empty-state');
                            if (container) container.style.display = 'none';
                            if (summary) summary.style.display = 'none';
                            if (empty) empty.style.display = 'block';
                        }, 450);
                    }
                }
            })
            .catch(err => console.error('Update error:', err));
        });
    });
});
