// jest.polyfill.js — runs before any test module is loaded
// Expose Node.js 18+ fetch globals to the jsdom environment.
// These are needed by msw v2 and the fetch-based API client.
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Node.js 18+ has native fetch — bridge it into the jsdom global scope
if (typeof globalThis.fetch !== "undefined") {
  global.fetch = globalThis.fetch;
  global.Headers = globalThis.Headers;
  global.Request = globalThis.Request;
  global.Response = globalThis.Response;
}
