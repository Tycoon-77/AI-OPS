import puppeteer from '../../frontend/node_modules/puppeteer-core/lib/esm/puppeteer/puppeteer-core.js';
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const backendDir = 'D:\\AI-OPS\\alertlens';
const frontendDir = 'D:\\AI-OPS\\frontend';

function checkHttp(url) {
  return new Promise((resolve) => {
    http.get(url, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    }).on('error', () => resolve(false));
  });
}

async function waitForHttp(url, maxRetries = 40) {
  for (let i = 0; i < maxRetries; i++) {
    await new Promise((r) => setTimeout(r, 800));
    if (await checkHttp(url)) return true;
  }
  return false;
}

async function run() {
  console.log('1. Starting backend...');
  const backend = spawn('D:\\AI-OPS\\python\\python.exe', [
    '-m', 'uvicorn', 'alertlens.api.main:app', '--port', '8000', '--app-dir', 'src'
  ], { cwd: backendDir, stdio: 'inherit' });

  console.log('2. Starting frontend...');
  const frontend = spawn('D:\\AI-OPS\\nodejs\\node.exe', [
    'node_modules/vite/bin/vite.js', '--port', '5173'
  ], { cwd: frontendDir, stdio: 'inherit' });

  console.log('3. Waiting for servers...');
  const backendUp = await waitForHttp('http://127.0.0.1:8000/api/health');
  const frontendUp = await waitForHttp('http://localhost:5173/');

  if (!backendUp || !frontendUp) {
    console.error('Failed to start servers. Backend:', backendUp, 'Frontend:', frontendUp);
    backend.kill();
    frontend.kill();
    process.exit(1);
  }

  console.log('4. Launching headless Chrome via puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.error('PAGE ERROR:', err));
  await page.setViewport({ width: 1440, height: 900 });

  console.log('5. Navigating to http://localhost:5173/ ...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });

  // Give React components a moment to finish rendering state
  await new Promise((r) => setTimeout(r, 4500));

  console.log('6. Taking LIVE screenshot...');
  const livePath = 'D:\\AI-OPS\\screenshot_live.png';
  await page.screenshot({ path: livePath, fullPage: false });
  console.log('Saved:', livePath);

  console.log('7. Killing backend to test unreachable state...');
  backend.kill('SIGKILL');

  // Trigger status refresh in frontend by reloading page
  console.log('8. Reloading page with backend dead...');
  await new Promise((r) => setTimeout(r, 1500));
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 3000));

  console.log('9. Taking DEMO / UNREACHABLE screenshot...');
  const demoPath = 'D:\\AI-OPS\\screenshot_demo.png';
  await page.screenshot({ path: demoPath, fullPage: false });
  console.log('Saved:', demoPath);

  await browser.close();
  frontend.kill('SIGKILL');
  console.log('Done successfully!');
  process.exit(0);
}

run().catch((err) => {
  console.error('Error during execution:', err);
  process.exit(1);
});
