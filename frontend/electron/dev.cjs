const http = require("node:http");
const { spawn } = require("node:child_process");

const viteUrl = "http://127.0.0.1:5173";
const shell = process.platform === "win32";
const npmCommand = "npm run dev -- --host 127.0.0.1";
const electronCommand = "npx electron .";

function waitForServer(url, attempts = 60) {
  return new Promise((resolve, reject) => {
    let remaining = attempts;

    const check = () => {
      const request = http.get(url, (response) => {
        response.resume();
        resolve();
      });

      request.on("error", () => {
        remaining -= 1;
        if (remaining <= 0) {
          reject(new Error(`Vite no respondio en ${url}`));
          return;
        }
        setTimeout(check, 500);
      });

      request.setTimeout(500, () => {
        request.destroy();
      });
    };

    check();
  });
}

const vite = spawn(npmCommand, {
  stdio: "inherit",
  shell,
});

vite.on("exit", (code) => {
  if (code !== 0) {
    process.exit(code ?? 1);
  }
});

waitForServer(viteUrl)
  .then(() => {
    const electron = spawn(electronCommand, {
      stdio: "inherit",
      shell,
      env: {
        ...process.env,
        ELECTRON_START_URL: viteUrl,
      },
    });

    electron.on("exit", (code) => {
      vite.kill();
      process.exit(code ?? 0);
    });
  })
  .catch((error) => {
    console.error(error.message);
    vite.kill();
    process.exit(1);
  });
