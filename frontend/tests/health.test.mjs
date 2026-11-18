import assert from "node:assert/strict";
import test from "node:test";
import { DEFAULT_API_BASE_URL, isHealthyResponse, resolveApiBaseUrl } from "../src/lib/health.ts";

test("uses the local backend on port 8001 by default", () => {
  assert.equal(resolveApiBaseUrl(), DEFAULT_API_BASE_URL);
  assert.equal(resolveApiBaseUrl("http://127.0.0.1:8001/"), DEFAULT_API_BASE_URL);
  assert.equal(resolveApiBaseUrl("  http://localhost:9000/// "), "http://localhost:9000");
});

test("accepts the documented healthy backend response", () => {
  assert.equal(isHealthyResponse({ status: "ok", api_version: "1.0.0", engine_available: true }), true);
});

test("rejects offline, malformed, and unavailable-engine responses", () => {
  assert.equal(isHealthyResponse({ status: "offline", api_version: "1.0.0", engine_available: false }), false);
  assert.equal(isHealthyResponse({ status: "ok", api_version: "1.0.0", engine_available: false }), false);
  assert.equal(isHealthyResponse({ status: "ok", engine_available: true }), false);
  assert.equal(isHealthyResponse(null), false);
});
