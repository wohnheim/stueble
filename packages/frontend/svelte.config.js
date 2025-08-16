import adapterStatic from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  compilerOptions: {
    runes: true,
  },

  preprocess: vitePreprocess(),

  kit: {
    adapter: adapterStatic({
      fallback: "index.html",
    }),
    csrf: {
      checkOrigin: false,
    },
  },
};

export default config;
