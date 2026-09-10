import { put } from "@vercel/blob";

const BLOB_PATH = "carc-queue-status.json";

function readBody(req) {
  if (req.body == null) return null;
  if (typeof req.body === "object") return req.body;
  try {
    return JSON.parse(String(req.body));
  } catch {
    return null;
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.setHeader("Allow", "POST");
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "method_not_allowed" }));
  }

  const expected = process.env.INGEST_SECRET;
  const auth = req.headers.authorization || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!expected || token !== expected) {
    res.statusCode = 401;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "unauthorized" }));
  }

  const body = readBody(req);
  if (!body || typeof body !== "object") {
    res.statusCode = 400;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "invalid_json" }));
  }

  try {
    await put(BLOB_PATH, JSON.stringify(body), {
      access: "private",
      addRandomSuffix: false,
      allowOverwrite: true,
      contentType: "application/json",
    });
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: true }));
  } catch (err) {
    res.statusCode = 500;
    res.setHeader("Content-Type", "application/json");
    return res.end(
      JSON.stringify({
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      })
    );
  }
}
