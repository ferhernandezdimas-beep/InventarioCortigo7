const toggle = document.querySelector('#menu-toggle');
const sidebar = document.querySelector('#sidebar');
toggle?.addEventListener('click', () => {
  const open = sidebar.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');
});
document.addEventListener('click', event => {
  if (sidebar?.classList.contains('open') && !sidebar.contains(event.target) && !toggle?.contains(event.target)) {
    sidebar.classList.remove('open');
    toggle?.setAttribute('aria-expanded', 'false');
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') { sidebar?.classList.remove('open'); toggle?.setAttribute('aria-expanded', 'false'); }
});
function connectivity() { const banner = document.querySelector('#connectivity'); if (banner) banner.hidden = navigator.onLine; }
window.addEventListener('online', connectivity);
window.addEventListener('offline', connectivity);
connectivity();
document.querySelectorAll('[data-submit-form]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!navigator.onLine) connectivity(); // Loopback can remain reachable without an Internet connection.
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
    if (!form.checkValidity()) return;
    const button = event.submitter || form.querySelector('button[type="submit"], button:not([type])');
    if (button?.name) {
      let submitted = form.querySelector('input[data-submitted-action]');
      if (!submitted) { submitted = document.createElement('input'); submitted.type = 'hidden'; submitted.dataset.submittedAction = 'true'; form.append(submitted); }
      submitted.name = button.name; submitted.value = button.value;
    }
    if (button) {
      button.dataset.originalText = button.textContent;
      button.disabled = true;
      button.textContent = 'Guardando…';
    }
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('button[data-original-text]').forEach(button => {
    button.disabled = false;
    button.textContent = button.dataset.originalText;
  });
});
function renumberLines(container, label) {
  [...container.children].forEach((row, index) => {
    row.querySelector('legend').textContent = `${label} ${index + 1}`;
    row.querySelectorAll('input, select, textarea').forEach(input => {
      input.name = input.name.replace(/lines-\d+-/, `lines-${index}-`);
      input.id = input.id.replace(/lines-\d+-/, `lines-${index}-`);
    });
    row.querySelectorAll('label').forEach(element => { element.htmlFor = element.htmlFor.replace(/lines-\d+-/, `lines-${index}-`); });
  });
  const counter = document.querySelector('#receipt-count');
  if (counter) counter.textContent = `${container.children.length} renglón(es)`;
}
function setupLines(containerId, buttonId, label, maximum) {
  const container = document.querySelector(containerId);
  const button = document.querySelector(buttonId);
  if (!container || !button) return;
  button.addEventListener('click', () => {
    if (container.children.length >= maximum) return;
    const clone = container.firstElementChild.cloneNode(true);
    clone.querySelectorAll('input, select, textarea').forEach(input => {
      input.value = input.tagName === 'SELECT' ? input.options[0]?.value ?? '' : '';
    });
    clone.querySelectorAll('.field-error').forEach(error => error.remove());
    container.append(clone);
    renumberLines(container, label);
    clone.querySelector('select')?.focus();
  });
  container.addEventListener('click', event => {
    const remove = event.target.closest('.remove-line');
    if (remove && container.children.length > 1) { remove.closest('fieldset').remove(); renumberLines(container, label); }
  });
  container.addEventListener('change', event => {
    if (!event.target.name.endsWith('-ingredient_id')) return;
    const row = event.target.closest('fieldset');
    const presentations = row.querySelector('select[name$="-presentation_id"]');
    if (!presentations) return;
    [...presentations.options].forEach(option => {
      if (!option.dataset.ingredient) return;
      const compatible = option.dataset.ingredient === event.target.value;
      option.hidden = !compatible;
      option.disabled = !compatible;
    });
    if (presentations.selectedOptions[0]?.disabled) presentations.value = '0';
  });
}
setupLines('#receipt-lines', '#add-receipt-line', 'Renglón', 30);
setupLines('#recipe-lines', '#add-recipe-line', 'Ingrediente', 60);
document.querySelector('#print-receipt')?.addEventListener('click', () => window.print());

const preview = document.querySelector('#fifo-preview');
if (preview) {
  const ingredient = document.querySelector('#ingredient_id');
  const quantity = document.querySelector('#quantity');
  let controller;
  let timer;
  async function updatePreview() {
    controller?.abort();
    if (!ingredient.value || !quantity.value) return;
    controller = new AbortController();
    preview.textContent = 'Consultando lotes disponibles…';
    try {
      const url = preview.dataset.url.replace(/\/0$/, `/${encodeURIComponent(ingredient.value)}`);
      const response = await fetch(`${url}?quantity=${encodeURIComponent(quantity.value)}`, { signal: controller.signal, headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (!response.ok) { preview.textContent = data.error || 'No se pudo consultar la disponibilidad.'; return; }
      const lots = data.allocations.map(a => `${a.lot}: ${a.quantity} ${a.unit}`).join(' · ');
      preview.textContent = `${data.sufficient ? 'Asignación prevista' : 'Existencia insuficiente'}: ${lots || 'Sin lotes elegibles'}. ${data.note}`;
    } catch (error) {
      if (error.name !== 'AbortError') preview.textContent = 'No se pudo consultar el inventario. Revisa tu conexión.';
    }
  }
  [ingredient, quantity].forEach(input => input.addEventListener('input', () => { clearTimeout(timer); controller?.abort(); timer = setTimeout(updatePreview, 250); }));
}

document.querySelector('#toggle-password')?.addEventListener('click', event => {
  const input = document.querySelector('#password');
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  event.currentTarget.textContent = show ? 'Ocultar' : 'Mostrar';
  event.currentTarget.setAttribute('aria-pressed', String(show));
});
