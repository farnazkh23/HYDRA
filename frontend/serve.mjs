import { createServer } from "node:http";
import { existsSync } from "node:fs";
import { execSync } from "node:child_process";

const PORT = parseInt(process.env.PORT || "3000", 10);

// Vinxi (no Lovable context) → .output/server/index.mjs
// Lovable build              → dist/server/server.js
const CANDIDATES = [".output/server/index.mjs", "dist/server/server.js"];
const entry = CANDIDATES.find(existsSync);

if (!entry) {
  console.error("[serve] No server entry found after build. Listing output:");
  try {
    console.error(
      execSync(
        'find . -maxdepth 6 \\( -name "*.mjs" -o -name "server.js" -o -name "index.js" \\) | grep -v node_modules | head -40',
      ).toString(),
    );
  } catch {}
  process.exit(1);
}

console.log(`[serve] Entry: ${entry}`);
const mod = await import(new URL(entry, import.meta.url));
const handler = mod.default ?? mod;

// Vinxi Node.js server — it calls listen() itself
if (typeof handler?.listen === "function") {
  handler.listen(PORT, () =>
    console.log(`[serve] Listening on port ${PORT}`),
  );
} else if (typeof handler?.fetch === "function") {
  // Cloudflare Workers-style handler — wrap in Node.js HTTP server
  const server = createServer(async (req, res) => {
    try {
      const host = req.headers.host || `localhost:${PORT}`;
      const url = `http://${host}${req.url}`;

      const headers = new Headers();
      for (const [k, v] of Object.entries(req.headers)) {
        if (v !== undefined)
          headers.set(k, Array.isArray(v) ? v.join(", ") : String(v));
      }

      let body = null;
      if (!["GET", "HEAD"].includes(req.method || "GET")) {
        const chunks = [];
        for await (const chunk of req) chunks.push(chunk);
        body = Buffer.concat(chunks);
      }

      const webRes = await handler.fetch(
        new Request(url, { method: req.method, headers, body }),
        {},
        {},
      );

      res.statusCode = webRes.status;
      webRes.headers.forEach((v, k) => res.setHeader(k, v));
      res.end(Buffer.from(await webRes.arrayBuffer()));
    } catch (err) {
      console.error("[serve] Error:", err);
      res.statusCode = 500;
      res.end("Internal Server Error");
    }
  });

  server.listen(PORT, () =>
    console.log(`[serve] HYDRA frontend on port ${PORT}`),
  );
} else {
  console.error("[serve] Entry has no usable interface:", Object.keys(handler ?? {}));
  process.exit(1);
}
