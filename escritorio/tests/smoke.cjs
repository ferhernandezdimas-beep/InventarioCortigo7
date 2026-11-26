const { app } = require('electron');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
app.setPath('userData', path.join(app.getPath('temp'), 'cortijo7-desktop-smoke-'+process.pid));
const { inspect } = require('../src/main.cjs');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function loaded() {
  for (let i=0; i<140; i++) {
    const { view, state } = inspect();
    if (view && !state.loading && !state.error && view.getVisible()) {
      const login = await view.webContents.executeJavaScript("!!document.querySelector('input[type=password]')");
      if (login) return inspect();
    }
    await delay(1000);
  }
  throw new Error('El escritorio no terminó de cargar Render.');
}
app.whenReady().then(async () => {
  try {
    const {win, view} = await loaded();
    const result = await view.webContents.executeJavaScript(`({title:document.title, login:!!document.querySelector('input[type="password"]'), node:typeof process, require:typeof require, bridge:typeof window.cortijo})`);
    console.log("Loaded",view.webContents.getURL(),result);
    await fs.mkdir(path.resolve(__dirname,"../../entrega/escritorio"),{recursive:true});
    await fs.writeFile(path.resolve(__dirname,"../../entrega/escritorio/arranque.png"),(await view.webContents.capturePage()).toPNG());
    assert.equal(result.login, true);assert.equal(result.node,'undefined');assert.equal(result.require,'undefined');assert.equal(result.bridge,'undefined');
    const shell = await win.webContents.executeJavaScript(`({bridge:typeof window.cortijo.command, title:document.title})`);
    assert.equal(shell.bridge,'function');
    assert.equal(await win.webContents.executeJavaScript(`window.cortijo.command('executeJavaScript')`), false);
    await view.webContents.executeJavaScript(`location.href='file:///etc/passwd';true`);
    await delay(600);assert.match(view.webContents.getURL(),/^https:\/\/cortijo7\.onrender\.com\//);
    console.log('Checking PDF');
    const pdf = await view.webContents.printToPDF({printBackground:true});assert.equal(pdf.subarray(0,4).toString(),'%PDF');
    const out=path.resolve(__dirname,'../../entrega/escritorio');await fs.mkdir(out,{recursive:true});
    await fs.writeFile(path.join(out,'vista-escritorio.png'),(await view.webContents.capturePage()).toPNG()).catch(()=>console.log('Captura gráfica no disponible.'));
    console.log('Checking offline');
    view.webContents.session.webRequest.onBeforeRequest({urls:['https://cortijo7.onrender.com/*']}, (_details, callback) => callback({cancel:true}));
    await view.webContents.session.clearCache();
    await view.webContents.loadURL('https://cortijo7.onrender.com/login?desktop-smoke='+Date.now()).catch(()=>{});
    await delay(1000);assert.ok(inspect().state.error);assert.equal(view.getVisible(),false);
    await fs.writeFile(path.join(out,'vista-sin-conexion.png'),(await win.webContents.capturePage()).toPNG()).catch(()=>console.log('Captura offline no disponible.'));
    view.webContents.session.webRequest.onBeforeRequest(null);
    await win.webContents.executeJavaScript(`window.cortijo.command('home')`);
    await loaded();
    console.log('SMOKE PASS: Render login, isolated renderers, narrow IPC, blocked file navigation, PDF, offline message and reconnection.');
    app.exit(0);
  } catch(error) { console.error(error); app.exit(1); }
});
setTimeout(()=>{console.error('Smoke timeout');app.exit(1)},180000).unref();
