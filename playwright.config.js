// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: {
    headless: true,
    baseURL: "http://localhost:3001",
    screenshot: "only-on-failure",
  },
  reporter: [["line"]],
});
