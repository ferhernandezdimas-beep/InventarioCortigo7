const SERVER = 'https://cortijo7.onrender.com';
const SHELL = 'c7desktop://app/index.html';
const COMMANDS = new Set(['home', 'back', 'forward', 'reload', 'print', 'pdf', 'zoom-in', 'zoom-out', 'zoom-reset']);
function serverURL(value = SERVER, packaged = true) {
  const u = new URL(value);
  if (u.username || u.password || u.search || u.hash || u.pathname !== '/') throw new Error('La conexión debe ser una dirección base sin credenciales.');
  if (u.origin !== SERVER && (packaged || u.protocol !== 'http:' || !['localhost', '127.0.0.1'].includes(u.hostname))) throw new Error('Servidor no permitido.');
  return u.origin;
}
function trustedURL(value, server = SERVER) {
  try { const u = new URL(value); return u.origin === server && !u.username && !u.password; } catch { return false; }
}
function shellResource(value) {
  try {
    const u = new URL(value);
    if (u.protocol !== 'c7desktop:' || u.hostname !== 'app' || u.username || u.password || u.search || u.hash) return null;
    return ({ '/index.html': 'index.html', '/shell.css': 'shell.css', '/shell.js': 'shell.js' })[u.pathname] || null;
  } catch { return null; }
}
function allowedCommand(value) { return typeof value === 'string' && COMMANDS.has(value); }
function downloadName(value) {
  const name = String(value).split(/[\\/]/).pop().replace(/[^\p{L}\p{N}._ -]/gu, '_').slice(-150);
  return /\.(csv|xlsx)$/i.test(name) ? name : null;
}
module.exports = { SERVER, SHELL, serverURL, trustedURL, shellResource, allowedCommand, downloadName };
