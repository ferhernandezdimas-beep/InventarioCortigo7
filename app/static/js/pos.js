const pos = document.querySelector('#pos');
if (pos) {
  const form = document.querySelector('#sale-form');
  const cartField = form.querySelector('#cart');
  const totalField = form.querySelector('#expected_total');
  const list = document.querySelector('#cart-rows');
  const status = document.querySelector('#cart-status');
  const total = document.querySelector('#cart-total');
  const confirm = document.querySelector('#confirm-sale');
  const cash = form.querySelector('#received');
  const method = form.querySelector('#method');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const currency = value => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(value);
  let cart = new Map();
  let controller;
  let sequence = 0;
  try {
    const saved = JSON.parse(cartField.value);
    if (Array.isArray(saved)) saved.forEach(line => {
      if (Number.isInteger(line.menu_item_id) && Number.isInteger(line.quantity) && line.quantity > 0 && line.quantity <= 9999) cart.set(line.menu_item_id, line.quantity);
    });
  } catch { cart = new Map(); }

  function serialize() {
    const lines = [...cart.entries()].map(([menu_item_id, quantity]) => ({ menu_item_id, quantity }));
    cartField.value = JSON.stringify(lines);
    return lines;
  }
  function element(tag, className, value) {
    const node = document.createElement(tag);
    node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }
  function render(rows) {
    list.replaceChildren();
    rows.forEach(row => {
      const wrapper = element('div', 'cart-row');
      const title = element('div', 'cart-row-title');
      title.append(element('span', '', row.name));
      const remove = element('button', 'text-button', 'Quitar');
      remove.type = 'button';
      remove.setAttribute('aria-label', `Quitar ${row.name}`);
      remove.addEventListener('click', () => { cart.delete(row.id); refresh(); });
      title.append(remove);
      const meta = element('div', 'cart-row-meta');
      const controls = element('div', 'cart-quantity');
      const minus = element('button', '', '−');
      const plus = element('button', '', '+');
      minus.type = plus.type = 'button';
      minus.setAttribute('aria-label', `Restar una unidad de ${row.name}`);
      plus.setAttribute('aria-label', `Agregar una unidad de ${row.name}`);
      const input = element('input', '');
      input.type = 'number'; input.min = '1'; input.max = '9999'; input.step = '1'; input.value = String(row.quantity);
      input.setAttribute('aria-label', `Cantidad de ${row.name}`);
      input.addEventListener('change', () => {
        const quantity = Number(input.value);
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 9999) { input.reportValidity(); return; }
        cart.set(row.id, quantity); refresh();
      });
      minus.addEventListener('click', () => { const count = cart.get(row.id); if (count <= 1) cart.delete(row.id); else cart.set(row.id, count - 1); refresh(); });
      plus.addEventListener('click', () => { cart.set(row.id, Math.min(9999, cart.get(row.id) + 1)); refresh(); });
      controls.append(minus, input, plus);
      meta.append(controls, element('strong', '', currency(row.subtotal)));
      wrapper.append(title, meta);
      list.append(wrapper);
    });
  }
  async function refresh() {
    controller?.abort();
    const current = ++sequence;
    const lines = serialize();
    confirm.disabled = true;
    totalField.value = '';
    status.classList.remove('has-error');
    if (!lines.length) {
      render([]); total.textContent = currency('0'); status.textContent = 'Selecciona un producto para iniciar la venta.'; return;
    }
    controller = new AbortController();
    status.textContent = 'Actualizando precios y total…';
    try {
      const response = await fetch(pos.dataset.quoteUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, Accept: 'application/json' }, body: JSON.stringify({ lines }), signal: controller.signal });
      if (current !== sequence) return;
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se pudo actualizar el carrito.');
      render(data.rows);
      total.textContent = currency(data.total);
      totalField.value = data.total;
      status.textContent = 'Total verificado. La disponibilidad se comprueba al confirmar.';
      confirm.disabled = false;
    } catch (error) {
      if (error.name === 'AbortError' || current !== sequence) return;
      status.textContent = `${error.message} Revisa la conexión o actualiza los productos.`;
      status.classList.add('has-error');
    }
  }
  pos.querySelectorAll('[data-product-id]').forEach(button => button.addEventListener('click', () => {
    const id = Number(button.dataset.productId);
    cart.set(id, Math.min(9999, (cart.get(id) || 0) + 1));
    refresh();
  }));
  document.querySelector('#clear-cart').addEventListener('click', () => { cart.clear(); refresh(); });
  function cashState() { cash.required = method.value === 'cash'; cash.closest('.field').hidden = method.value !== 'cash'; }
  method.addEventListener('change', cashState);
  cashState();
  const search = document.querySelector('#pos-search');
  const category = document.querySelector('#pos-category');
  function filter() {
    let visible = 0;
    pos.querySelectorAll('[data-product-id]').forEach(button => {
      button.hidden = !button.dataset.name.includes(search.value.trim().toLowerCase()) || (category.value !== '' && button.dataset.category !== category.value);
      if (!button.hidden) visible++;
    });
    const empty = document.querySelector('#pos-filter-empty');
    if (empty) empty.hidden = visible > 0;
  }
  search.addEventListener('input', filter);
  category.addEventListener('change', filter);
  refresh();
}
