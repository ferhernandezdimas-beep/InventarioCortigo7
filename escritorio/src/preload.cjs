const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('cortijo', {
  command: (action) => ipcRenderer.invoke('desktop:command', action),
  onState: (callback) => {
    if (typeof callback !== 'function') return;
    const listener = (_event, state) => callback(state);
    ipcRenderer.on('desktop:state', listener);
    ipcRenderer.invoke('desktop:state').then(callback);
    return () => ipcRenderer.removeListener('desktop:state', listener);
  }
});
