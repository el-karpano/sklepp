const Cart = {
    KEY: 'sklepp_cart',

    getItems() {
        try {
            return JSON.parse(localStorage.getItem(this.KEY)) || [];
        } catch {
            return [];
        }
    },

    save(items) {
        localStorage.setItem(this.KEY, JSON.stringify(items));
        this.updateBadge();
    },

    add(product) {
        const items = this.getItems();
        const moq = product.min_order || 1;
        const existing = items.find(i => i.id === product.id);
        if (existing) {
            existing.quantity += moq;
        } else {
            items.push({
                id: product.id,
                name: product.name,
                price_byn: product.price_byn,
                price_rub: product.price_rub,
                image_url: product.image_url || null,
                min_order: moq,
                quantity: moq
            });
        }
        this.save(items);
    },

    remove(productId) {
        const items = this.getItems().filter(i => i.id !== productId);
        this.save(items);
    },

    updateQuantity(productId, quantity) {
        const items = this.getItems();
        const item = items.find(i => i.id === productId);
        if (item) {
            const moq = item.min_order || 1;
            if (quantity < moq) {
                this.remove(productId);
                return;
            }
            item.quantity = quantity;
            this.save(items);
        }
    },

    getCount() {
        return this.getItems().reduce((sum, i) => sum + i.quantity, 0);
    },

    getTotalByn() {
        return this.getItems().reduce((sum, i) => sum + (parseFloat(i.price_byn) || 0) * i.quantity, 0);
    },

    getTotalRub() {
        return this.getItems().reduce((sum, i) => sum + (parseFloat(i.price_rub) || 0) * i.quantity, 0);
    },

    clear() {
        localStorage.removeItem(this.KEY);
        this.updateBadge();
    },

    updateBadge() {
        const badge = document.getElementById('cart-badge');
        if (badge) {
            const count = this.getCount();
            badge.textContent = count;
            badge.style.display = count > 0 ? 'flex' : 'none';
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Cart.updateBadge());
