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

    add(product, variant) {
        const items = this.getItems();
        const moq = product.min_order || 1;
        const v = variant || 1;
        const key = product.id + '_v' + v;
        const existing = items.find(i => i.id === product.id && (i.variant || 1) === v);
        if (existing) {
            existing.quantity += moq;
        } else {
            items.push({
                id: product.id,
                name: product.name,
                price_byn: product.price_byn,
                price_rub: product.price_rub,
                image_url: product.image_url || null,
                image_url_2: product.image_url_2 || null,
                min_order: moq,
                quantity: moq,
                variant: v
            });
        }
        this.save(items);
    },

    remove(productId, variant) {
        const v = variant || 1;
        const items = this.getItems().filter(i => !(i.id === productId && (i.variant || 1) === v));
        this.save(items);
    },

    updateQuantity(productId, quantity, variant) {
        const items = this.getItems();
        const v = variant || 1;
        const item = items.find(i => i.id === productId && (i.variant || 1) === v);
        if (item) {
            const moq = item.min_order || 1;
            if (quantity < moq) {
                this.remove(productId, v);
                return;
            }
            item.quantity = quantity;
            this.save(items);
        }
    },

    updateVariant(productId, oldVariant, newVariant) {
        const items = this.getItems();
        const ov = oldVariant || 1;
        const nv = newVariant || 1;
        if (ov === nv) return;
        const existing = items.find(i => i.id === productId && (i.variant || 1) === nv);
        const item = items.find(i => i.id === productId && (i.variant || 1) === ov);
        if (!item) return;
        if (existing) {
            existing.quantity += item.quantity;
            this.save(items.filter(i => !(i.id === productId && (i.variant || 1) === ov)));
        } else {
            item.variant = nv;
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
