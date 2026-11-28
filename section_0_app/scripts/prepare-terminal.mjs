import { copyFile, mkdir } from "node:fs/promises";

const app = new URL("../", import.meta.url);
const destination = new URL("src/vendor/xterm/", app);
await mkdir(destination, { recursive: true });

const assets = {
  "xterm.mjs": "@xterm/xterm/lib/xterm.mjs",
  "xterm.css": "@xterm/xterm/css/xterm.css",
  "addon-fit.mjs": "@xterm/addon-fit/lib/addon-fit.mjs",
  "LICENSE-xterm": "@xterm/xterm/LICENSE",
  "LICENSE-addon-fit": "@xterm/addon-fit/LICENSE",
};
await Promise.all(Object.entries(assets).map(([name, source]) =>
  copyFile(new URL(`node_modules/${source}`, app), new URL(name, destination)),
));
