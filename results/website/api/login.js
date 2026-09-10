async function tokenFor(password) {
  const data = new TextEncoder().encode(`liralab-gate:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function readBody(req) {
  if (req.body == null) return {};
  if (typeof req.body === "object") return req.body;
  try {
    return JSON.parse(String(req.body));
  } catch {
    return {};
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.setHeader("Allow", "POST");
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "method_not_allowed" }));
  }

  const expected = process.env.SITE_PASSWORD;
  if (!expected) {
    res.statusCode = 500;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "password_not_configured" }));
  }

  const { password } = readBody(req);
  if (String(password ?? "") !== expected) {
    res.statusCode = 401;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "invalid_password" }));
  }

  const token = await tokenFor(expected);
  const secure = process.env.VERCEL ? "; Secure" : "";
  res.setHeader(
    "Set-Cookie",
    `lira_gate=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000${secure}`
  );
  res.statusCode = 200;
  res.setHeader("Content-Type", "application/json");
  return res.end(JSON.stringify({ ok: true }));
}
