const { app, BrowserWindow, shell } = require("electron");
const path = require("node:path");

const isDev = Boolean(process.env.ELECTRON_START_URL);

function createWindow() {
  const window = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1100,
    minHeight: 720,
    title: "DistriCare",
    backgroundColor: "#F7FAFC",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.removeMenu();
  window.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev) {
    window.loadURL(process.env.ELECTRON_START_URL);
  } else {
    window.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
