const nextJest = require("next/jest");

const createJestConfig = nextJest({ dir: "./" });

module.exports = createJestConfig({
  testEnvironment: "jest-environment-jsdom",
  testEnvironmentOptions: { customExportConditions: [""] },
  setupFiles: ["<rootDir>/jest.polyfill.js"],
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  testMatch: ["**/__tests__/**/*.test.{ts,tsx}"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
    "!src/app/**",          // Next.js framework layout/page files
    "!src/__tests__/**",    // test infrastructure
    "!src/lib/api.ts",      // HTTP adapter — mocked in all tests
  ],
  coverageThreshold: { global: { lines: 80 } },
});
