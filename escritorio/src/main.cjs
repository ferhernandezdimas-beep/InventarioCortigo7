const { app, BrowserWindow, WebContentsView, Menu, session, ipcMain, protocol, net, dialog } = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const { pathToFileURL } = require('node:url');
const { SERVER, SHELL, serverURL, trustedURL, shellResource, allowedCommand, downloadName } = require('./policy.cjs');
protocol.registerSchemesAsPrivileged([{ scheme: 'c7desktop', privileges: { standard: true, secure: true, supportFetchAPI: true } }]);
app.setName('Cortijo 7');
let win, view, server, quitting = false;
let state = { loading: true, error: '', canBack: false, canForward: false };
function notify(patch = {}) {
  state = { ...state, ...patch };
  if (view && !view.webContents.isDestroyed()) {
    state.canBack = view.webContents.navigationHistory.canGoBack();
    state.canForward = view.webContents.navigationHistory.canGoForward();
  }
  if (win && !win.isDestroyed()) win.webContents.send('desktop:state', state);
}
function layout() {
  if (!win || !view) return;
  const [width, height] = win.getContentSize();
  view.setBounds({ x: 0, y: 64, width, height: Math.max(0, height - 64) });
}
function fail() {
  if (quitting || !view || view.webContents.isDestroyed()) return;
  view.setVisible(false);
  notify({ loading: false, error: 'No hay conexión con el servidor. Comprueba internet y vuelve a conectar. Si estabas guardando una operación, revisa su resultado en Movimientos o Ventas antes de repetirla. Esta aplicación no guarda operaciones offline.' });
}
function home() {
  notify({ loading: true, error: '' });
  view.setVisible(false);
  return view.webContents.loadURL(server).catch(fail);
}
async function command(action) {
  if (!allowedCommand(action) || !view || view.webContents.isDestroyed()) return false;
  const wc = view.webContents;
  switch (action) {
    case 'home': await home(); break;
    case 'back': if (wc.navigationHistory.canGoBack()) wc.navigationHistory.goBack(); break;
    case 'forward': if (wc.navigationHistory.canGoForward()) wc.navigationHistory.goForward(); break;
    case 'reload':
      if (state.error) await home();
      else {
        const result = await dialog.showMessageBox(win, { type: 'question', message: '¿Actualizar esta pantalla?', detail: 'Los campos que todavía no guardaste pueden perderse.', buttons: ['Cancelar', 'Actualizar'], defaultId: 0, cancelId: 0 });
        if (result.response === 1) wc.reload();
      }
      break;
    case 'print': if (!state.error && !state.loading) wc.print({ silent: false, printBackground: true }, (ok, reason) => { if (!ok && !/cancel/i.test(reason)) dialog.showMessageBox(win, { type: 'error', message: 'No fue posible imprimir el documento.' }); }); break;
    case 'pdf': {
      if (state.error || state.loading || !trustedURL(wc.getURL(), server)) break;
      const result = await dialog.showSaveDialog(win, { title: 'Guardar pantalla como PDF', defaultPath: path.join(app.getPath('documents'), 'Cortijo7.pdf'), filters: [{ name: 'PDF', extensions: ['pdf'] }] });
      if (!result.canceled && result.filePath) await fs.writeFile(result.filePath, await wc.printToPDF({ printBackground: true, preferCSSPageSize: true }));
      break;
    }
    case 'zoom-in': wc.setZoomLevel(Math.min(3, wc.getZoomLevel() + 0.5)); break;
    case 'zoom-out': wc.setZoomLevel(Math.max(-2, wc.getZoomLevel() - 0.5)); break;
    case 'zoom-reset': wc.setZoomLevel(0); break;
  }
  return true;
}
function localSender(event) { return win && event.sender === win.webContents && event.senderFrame === win.webContents.mainFrame && event.senderFrame.url === SHELL; }
function menu() {
  const run = (action) => () => { void command(action).catch(() => dialog.showMessageBox(win, { type: 'error', message: 'No fue posible completar esta acción.' })); };
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(process.platform === 'darwin' ? [{ role: 'appMenu', label: 'Cortijo 7' }] : []),
    { label: 'Archivo', submenu: [{ label: 'Inicio', accelerator: 'CmdOrCtrl+H', click: run('home') }, { label: 'Imprimir', accelerator: 'CmdOrCtrl+P', click: run('print') }, { label: 'Guardar PDF', accelerator: 'CmdOrCtrl+Shift+S', click: run('pdf') }, { type: 'separator' }, { role: process.platform === 'darwin' ? 'close' : 'quit', label: 'Cerrar' }] },
    { label: 'Edición', submenu: [{ role: 'undo', label: 'Deshacer' }, { role: 'redo', label: 'Rehacer' }, { type: 'separator' }, { role: 'cut', label: 'Cortar' }, { role: 'copy', label: 'Copiar' }, { role: 'paste', label: 'Pegar' }, { role: 'selectAll', label: 'Seleccionar todo' }] },
    { label: 'Vista', submenu: [{ label: 'Actualizar', accelerator: 'CmdOrCtrl+R', click: run('reload') }, { label: 'Acercar', accelerator: 'CmdOrCtrl+Plus', click: run('zoom-in') }, { label: 'Alejar', accelerator: 'CmdOrCtrl+-', click: run('zoom-out') }, { label: 'Tamaño original', accelerator: 'CmdOrCtrl+0', click: run('zoom-reset') }, { role: 'togglefullscreen', label: 'Pantalla completa' }] },
    { label: 'Ayuda', submenu: [{ label: 'Acerca de Cortijo 7', click: () => dialog.showMessageBox(win, { title: 'Cortijo 7', message: `Cortijo 7 · Escritorio ${app.getVersion()}`, detail: 'Sistema de gestión integral conectado a Render. Utiliza los mismos usuarios y roles que la web. Las operaciones requieren conexión a internet.' }) }] }
  ]));
}
function createWindow() {
  const remoteSession = session.fromPartition('persist:cortijo7-web-v1');
  remoteSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  remoteSession.setPermissionCheckHandler(() => false);
  win = new BrowserWindow({ width: 1440, height: 940, minWidth: 960, minHeight: 640, show: false, backgroundColor: '#f7f6f2', title: 'Cortijo 7', icon: path.join(__dirname, '../assets/icon.png'), webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: true, nodeIntegration: false, webSecurity: true, devTools: !app.isPackaged } });
  view = new WebContentsView({ webPreferences: { session: remoteSession, contextIsolation: true, sandbox: true, nodeIntegration: false, webSecurity: true, allowRunningInsecureContent: false, webviewTag: false, devTools: !app.isPackaged, safeDialogs: true, navigateOnDragDrop: false } });
  win.contentView.addChildView(view); view.setVisible(false); layout();
  win.on('resize', layout);
  win.on('closed', () => { if (view && !view.webContents.isDestroyed()) view.webContents.close(); view = null; win = null; });
  win.webContents.on('will-navigate', (event, url) => { if (url !== SHELL) event.preventDefault(); });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  view.webContents.setWindowOpenHandler(({ url }) => { if (trustedURL(url, server)) void view.webContents.loadURL(url).catch(fail); return { action: 'deny' }; });
  const restrict = (event, url) => { if (!trustedURL(url, server)) event.preventDefault(); };
  view.webContents.on('will-navigate', restrict);
  view.webContents.on('will-redirect', restrict);
  view.webContents.on('will-attach-webview', (event) => event.preventDefault());
  view.webContents.on('did-start-loading', () => notify({ loading: true }));
  view.webContents.on('did-stop-loading', () => notify({ loading: false }));
  view.webContents.on('did-finish-load', () => { if (trustedURL(view.webContents.getURL(), server) && !state.error) { view.setVisible(true); notify({ loading: false, error: '' }); } });
  view.webContents.on('did-navigate-in-page', () => notify());
  view.webContents.on('did-fail-load', (_e, code, _description, _url, isMainFrame) => { if (isMainFrame && code !== -3) fail(); });
  view.webContents.on('render-process-gone', fail);
  remoteSession.removeAllListeners('will-download');
  remoteSession.on('will-download', (event, item, source) => {
    const filename = downloadName(item.getFilename());
    if (source !== view?.webContents || !filename || !item.getURLChain().every(url => trustedURL(url, server))) { event.preventDefault(); return; }
    item.setSaveDialogOptions({ title: 'Guardar documento de Cortijo 7', defaultPath: path.join(app.getPath('downloads'), filename), filters: [{ name: 'Documento', extensions: [filename.split('.').pop()] }] });
    item.once('done', (_event, result) => { if (result !== 'completed' && result !== 'cancelled' && win) dialog.showMessageBox(win, { type: 'error', message: 'La descarga no se completó. Vuelve a exportar el documento.' }); });
  });
  void win.loadURL(SHELL).then(() => { win.show(); void home(); });
  menu();
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.show(); win.focus(); } });
  app.on('before-quit', () => { quitting = true; });
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
  app.on('activate', () => { if (!win) createWindow(); });
  app.whenReady().then(() => {
    server = serverURL(process.env.CORTIJO7_DESKTOP_URL || SERVER, app.isPackaged);
    protocol.handle('c7desktop', request => {
      const file = shellResource(request.url);
      return file ? net.fetch(pathToFileURL(path.join(__dirname, file)).href) : new Response('Not found', { status: 404 });
    });
    ipcMain.handle('desktop:command', (event, action) => { if (!localSender(event) || !allowedCommand(action)) return false; return command(action); });
    ipcMain.handle('desktop:state', event => localSender(event) ? state : null);
    createWindow();
  }).catch(error => { dialog.showErrorBox('Cortijo 7', error.message); app.quit(); });
}
// Main-process inspection only; no inspection API is exposed to either renderer.
module.exports = { inspect: () => ({ win, view, state }) };
