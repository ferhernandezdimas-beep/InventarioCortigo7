for (const button of document.querySelectorAll('[data-command]')) {
  button.addEventListener('click', () => window.cortijo.command(button.dataset.command).catch(() => {}));
}
window.cortijo.onState((state) => {
  document.getElementById('back').disabled = !state.canBack;
  document.getElementById('forward').disabled = !state.canForward;
  document.getElementById('connection').textContent = state.error ? 'Sin conexión al sistema' : state.loading ? 'Conectando…' : 'Conectado a Render';
  document.getElementById('heading').textContent = state.error ? 'No pudimos abrir el sistema' : 'Conectando con Cortijo 7';
  document.getElementById('message').textContent = state.error || 'Estamos abriendo tu espacio de trabajo. El primer acceso puede tardar un momento.';
  document.getElementById('retry').hidden = !state.error;
  for (const command of ['print', 'pdf']) document.querySelector(`[data-command="${command}"]`).disabled = !!state.error || state.loading;
});
