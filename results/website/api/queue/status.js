import { get } from "@vercel/blob";

const BLOB_PATH = "carc-queue-status.json";

async function readStream(stream) {
  const chunks = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET");
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "method_not_allowed" }));
  }

  const empty = {
    ok: false,
    error: "No queue snapshot yet.",
    hint: "Keep carc/dashboard/server.py running locally (VPN + ssh discovery). It pushes snapshots here.",
  };

  try {
    const result = await get(BLOB_PATH, { access: "private" });
    if (!result || result.statusCode !== 200 || !result.stream) {
      res.statusCode = 200;
      res.setHeader("Content-Type", "application/json");
      return res.end(JSON.stringify(empty));
    }

    const text = await readStream(result.stream);
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "private, no-store");
    return res.end(text);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    return res.end(
      JSON.stringify({
        ...empty,
        error: /not found|404/i.test(message) ? empty.error : message,
      })
    );
  }
}
