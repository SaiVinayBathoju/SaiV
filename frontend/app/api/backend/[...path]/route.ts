/**
 * Proxy API route: forwards requests to the FastAPI backend.
 * Ensures multipart file uploads (e.g. PDF from Media) are correctly forwarded.
 */

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, await params);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, await params);
}

async function proxy(
  request: Request,
  { path }: { path: string[] }
) {
  const pathStr = path?.length ? path.join("/") : "";
  const url = `${BACKEND_URL}/${pathStr}`;
  const method = request.method;

  try {
    // For POST/PUT with body, forward the request body and headers
    const contentType = request.headers.get("content-type") || "";

    let body: BodyInit | undefined;
    const headers: Record<string, string> = {};

    if (method !== "GET" && method !== "HEAD") {
      if (contentType.includes("multipart/form-data")) {
        // Forward multipart (file upload) as-is so boundary is preserved
        body = await request.arrayBuffer();
        headers["content-type"] = contentType;
      } else {
        body = await request.text();
        if (body && !contentType.includes("multipart")) {
          headers["content-type"] = contentType || "application/json";
        }
      }
    }

    const res = await fetch(url, {
      method,
      headers: {
        ...headers,
        accept: request.headers.get("accept") || "application/json",
      },
      body,
    });

    const resContentType = res.headers.get("content-type") || "";
    const text = await res.text();

    return new Response(text, {
      status: res.status,
      statusText: res.statusText,
      headers: {
        "content-type": resContentType,
      },
    });
  } catch (err) {
    console.error("[api/backend proxy error]", url, err);
    return new Response(
      JSON.stringify({
        detail:
          "Backend unreachable. Is the FastAPI server running on port 8000?",
      }),
      {
        status: 502,
        headers: { "content-type": "application/json" },
      }
    );
  }
}
