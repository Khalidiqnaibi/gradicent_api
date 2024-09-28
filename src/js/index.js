const { app, BrowserWindow, ipcMain } = require('electron');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: true,  // Set this to true
      contextIsolation: true,
      preload: __dirname + "/preload.js",
    },
  });

  mainWindow.loadFile('home.html');

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function () {
  if (mainWindow === null) createWindow();
});

ipcMain.on('opdata', (event,data) => {
  //mainWindow.loadFile('data.html');
  console.log(data);
  mainWindow.webContents.send('pdata', data);
});

ipcMain.on('potato', () => {
  message='potato'
  mainWindow.webContents.send('appdata', message);
});

// Example: Listen for the 'openFile' event and call the corresponding Python function
ipcMain.on('openFile', (event, path) => {
    //window.BinderApi.outt(path)
    mainWindow.webContents.send('outt', path);
});

// Repeat the above pattern for other functions
