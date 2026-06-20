/**
 * Node.js HTTP adapter for TanStack Start / Vinxi SSR output.
 *
 * Tries Vinxi's default output (.output/server/index.mjs) first.
 * Falls back to wrapping the Cloudflare-Worker-style fetch handler
 * in dist/server/server.js with a plain Node.js HTTP server.
 */
import { createServer } from "node:http";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const PORT = parseInt(process.env.PORT || "3000", 10);
const __dir = new URL(".", import.meta.url).pathname;

// ── 1. Try the Vinxi/Nitro Node.js server (has its own listen()) ──────────
const vinxiEntry = resolve(__dir, ".output/server/index.mjs");
if (existsSync(vinxiEntry)) {
  console.log(`[server-node] Starting Vinxi server: ${vinxiEntry}`);
  await import(pathToFileURL(vinxiEntry).href);
  // Vinxi calls listen() internally; nothing else to do.
} else {
  // ── 2. Wrap the Cloudflare-Worker fetch handler ──────────────────────────
  console.log("[server-node] Vinxi output not found — wrapping fetch handler");

  const candidates = [
    resolve(__dir, "dist/server/server.js"),
    resolve(__dir, "dist/server/assets/server.js"),
  ];

  let fetchHandler;
  for (const p of candidates) {
    if (existsSync(p)) {
      const mod = await import(pathToFileURL(p).href);
      fetchHandler = mod.default?.fetch ?? mod.fetch ?? mod.default;
      if (typeof fetchHandler === "function") break;
      // module exports { fetch } directly
      if (mod.default && typeof mod.default.fetch === "function") {
        fetchHandler = mod.default.fetch.bind(mod.default);
        break;
      }
    }
  }

  if (!fetchHandler) {
    console.error("[server-node] No server entry found. Searched:");
    candidates.forEach((c) => console.error(" -", c));
    process.exit(1);
  }

  const server = createServer(async (req, res) => {
    const url = `http://localhost:${PORT}${req.url}`;
    const headers = Object.fromEntries(
      Array.from({ length: req.rawHeaders.length / 2 }, (_, i) => [
        req.rawHeaders[i * 2],
        req.rawHeaders[i * 2 + 1],
      ])
    );

    let body = undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      body = await new Promise((resolve) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => resolve(Buffer.concat(chunks)));
      });
    }

    try {
      const response = await fetchHandler(
        new Request(url, { method: req.method, headers, body }),
        {},
        {}
      );
      res.writeHead(response.status, Object.fromEntries(response.headers));
      const buf = await response.arrayBuffer();
      res.end(Buffer.from(buf));
    } catch (err) {
      console.error("[server-node] Handler error:", err);
      res.writeHead(500);
      res.end("Internal Server Error");
    }
  });

  server.listen(PORT, () =>
    console.log(`[server-node] Listening on port ${PORT}`)
  );
}
