/// <reference types="@cloudflare/workers-types" />

interface Env {
  API_HOSTNAME: string;
}

export const onRequest: PagesFunction<Env> = (context) => {
  try {
    const url = new URL(context.request.url);
    if (url.pathname.startsWith("/api")) {
      const host = context.env.API_HOSTNAME;
      if (!host) throw new Error("Undefined environment variable");

      const newUrl = new URL(context.request.url);

      newUrl.host = new URL(`https://${host}`).host;
      newUrl.pathname = url.pathname.replace("/api", "");

      const modifiedRequest = new Request(newUrl, context.request);
      const xRealIp = context.request.headers.get("x-real-ip");
      if (xRealIp !== null)
        modifiedRequest.headers.set("x-request-ip", xRealIp);
      return fetch(modifiedRequest);
    }
    return context.next();
  } catch (e) {
    console.log(e);
    return context.next();
  }
};
