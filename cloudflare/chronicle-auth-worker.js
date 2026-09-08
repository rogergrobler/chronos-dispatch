/**
 * Basic Auth gate in front of the Chronicle host.
 *
 * GitHub Pages cannot do HTTP Basic Auth. noindex/robots.txt are not
 * access control. Deploy this Worker on a custom domain and point
 * DISPATCH_BASE_URL (GitHub Actions variable) at that domain.
 *
 * Secrets (wrangler secret put): BASIC_AUTH_USER, BASIC_AUTH_PASS
 * Var: ORIGIN = https://rogergrobler.github.io/chronos-dispatch
 */
function safeEqual(a, b) {
  const left = String(a);
  const right = String(b);
  if (left.length !== right.length) return false;
  let out = 0;
  for (let i = 0; i < left.length; i++) {
    out |= left.charCodeAt(i) ^ right.charCodeAt(i);
  }
  return out === 0;
}

export default {
  async fetch(request, env) {
    const user = env.BASIC_AUTH_USER || "";
    const pass = env.BASIC_AUTH_PASS || "";
    if (!user || !pass) {
      return new Response("Auth worker misconfigured", { status: 500 });
    }

    const header = request.headers.get("Authorization") || "";
    const expected = "Basic " + btoa(`${user}:${pass}`);
    if (!safeEqual(header, expected)) {
      return new Response("Partner credentials required", {
        status: 401,
        headers: {
          "WWW-Authenticate": 'Basic realm="Chronos Chronicle"',
          "Cache-Control": "no-store",
          "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
      });
    }

    const origin = (env.ORIGIN || "").replace(/\/$/, "");
    if (!origin) {
      return new Response("ORIGIN unset", { status: 500 });
    }

    const incoming = new URL(request.url);
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405, headers: { "Cache-Control": "no-store" } });
    }
    const target = origin + incoming.pathname + incoming.search;
    const upstream = await fetch(target, {
      method: request.method,
      redirect: "follow",
      headers: { "User-Agent": request.headers.get("User-Agent") || "chronicle-auth" },
    });

    const out = new Response(upstream.body, upstream);
    out.headers.delete("Access-Control-Allow-Origin");
    out.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet");
    out.headers.set("Cache-Control", "private, max-age=60");
    return out;
  },
};
