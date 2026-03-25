/// <reference types="@cloudflare/workers-types" />

interface Env {
  REDIRECT_URL: string;
}

export const onRequest: PagesFunction<Env> = (context) => {
  try {
    const redirect = context.env.REDIRECT_URL;
    if (!redirect) throw new Error("Undefined environment variable");

    return new Response(`Moved Permanently. Redirecting to ${redirect}`, {
      status: 301,
      headers: {
        location: redirect,
      },
    });
  } catch (e) {
    console.log(e);
    return context.next();
  }
};
