export default {
  async fetch(request) {
    const incomingUrl = new URL(request.url);
    const targetUrl = incomingUrl.searchParams.get("url");

    if (!targetUrl) {
      return new Response("Missing ?url= parameter", { status: 400 });
    }

    try {
      const response = await fetch(targetUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
      });

      const body = await response.text();

      return new Response(body, {
        status: response.status,
        headers: {
          "Content-Type": response.headers.get("Content-Type") || "text/html; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (err) {
      return new Response(`Proxy fetch failed: ${err.message}`, { status: 502 });
    }
  },
};
