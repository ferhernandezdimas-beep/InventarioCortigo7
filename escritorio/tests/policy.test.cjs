const test = require('node:test');
const assert = require('node:assert/strict');
const { SERVER, serverURL, trustedURL, shellResource, allowedCommand, downloadName } = require('../src/policy.cjs');
test('production only connects to the configured HTTPS service', () => {
 assert.equal(serverURL(), SERVER);
 for (const u of ['http://cortijo7.onrender.com', 'https://cortijo7.onrender.com.evil.test', 'https://user:pass@cortijo7.onrender.com', 'https://cortijo7.onrender.com/?token=x', 'http://127.0.0.1:8077']) assert.throws(() => serverURL(u));
 assert.equal(serverURL('http://127.0.0.1:8077', false), 'http://127.0.0.1:8077');
});
test('navigation refuses local files, injected protocols and credentials', () => {
 assert.equal(trustedURL(SERVER+'/inventario'), true);
 for (const u of ['file:///etc/passwd', 'javascript:alert(1)', 'https://cortijo7.onrender.com@evil.test', 'https://user:pass@cortijo7.onrender.com', SERVER+'.evil.test']) assert.equal(trustedURL(u), false);
});
test('local protocol exposes exactly three shell assets', () => {
 assert.equal(shellResource('c7desktop://app/index.html'), 'index.html');
 for (const u of ['c7desktop://app/main.cjs', 'c7desktop://app/preload.cjs', 'c7desktop://app/../../package.json', 'file:///index.html', 'c7desktop://other/index.html']) assert.equal(shellResource(u), null);
});
test('IPC commands contain no arbitrary URL, path or execution primitive', () => {
 assert.equal(allowedCommand('pdf'), true);
 for (const c of ['openExternal', 'executeJavaScript', 'https://evil.test', {}, null]) assert.equal(allowedCommand(c), false);
});
test('downloads retain safe report filenames and reject executable or HTML payloads', () => {
 assert.equal(downloadName('../../ventas.csv'), 'ventas.csv');
 assert.equal(downloadName('inventario.xlsx'), 'inventario.xlsx');
 for (const f of ['invoice.exe', 'report.csv.exe', 'session.html', '.env']) assert.equal(downloadName(f), null);
});
