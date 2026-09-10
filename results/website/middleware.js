async function tokenFor(password) {
  const data = new TextEncoder().encode(`liralab-gate:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function cookieValue(req, name) {
  const raw = req.headers.get("cookie") || "";
  const parts = raw.split(/;\s*/);
  for (const part of parts) {
    const i = part.indexOf("=");
    if (i === -1) continue;
    if (part.slice(0, i) === name) return part.slice(i + 1);
  }
  return null;
}

export const config = {
  matcher: [
    "/((?!login(?:\\.html)?|api/login|api/queue/ingest|styles\\.css|favicon\\.ico).*)",
  ],
};

export default async function middleware(request) {
  const password = process.env.SITE_PASSWORD;
  if (!password) {
    return new Response("Site password is not configured.", { status: 500 });
  }

  const expected = await tokenFor(password);
  const got = cookieValue(request, "lira_gate");
  if (got && got === expected) return;

  const url = new URL(request.url);
  url.pathname = "/login";
  url.search = "";
  return Response.redirect(url, 302);
}
