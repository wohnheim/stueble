import { sveltekit } from "@sveltejs/kit/vite";
import { SvelteKitPWA } from "@vite-pwa/sveltekit";
import type { ConfigEnv, UserConfig } from "vite";
import EnvironmentPlugin from "vite-plugin-environment";
import type { ManifestOptions } from "vite-plugin-pwa";
import { viteStaticCopy } from "vite-plugin-static-copy";

export default async function (config: ConfigEnv): Promise<UserConfig> {
  return {
    plugins: [
      EnvironmentPlugin(["NODE_ENV"]),
      sveltekit(),
      SvelteKitPWA({
        srcDir: "src",
        filename: "service-worker.ts",
        registerType: "prompt",
        strategies: "injectManifest",
        injectManifest: {
          globPatterns: ["**/*.{js,css,html,woff2}"],
        },
        manifest: (await import(
          "./static/manifest.json"
        )) as Partial<ManifestOptions>,
      }),
      viteStaticCopy({
        targets: [
          {
            src: [
              "node_modules/@stoplight/elements/web-components.min.js",
              "node_modules/@stoplight/elements/styles.min.css",
              "node_modules/@webcomponents/webcomponentsjs/webcomponents-bundle.js",
              "node_modules/@asyncapi/web-component/lib/asyncapi-web-component.js",
              "node_modules/@asyncapi/react-component/styles/default.min.css",
            ],
            dest: "api-spec/assets",
            rename: { stripBase: 1 },
          },
        ],
      }),
    ],
    ssr: {
      noExternal: ["beercss"],
    },
  };
}
