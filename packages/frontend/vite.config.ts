import { sveltekit } from "@sveltejs/kit/vite";
import type { ConfigEnv, UserConfig } from "vite";
import EnvironmentPlugin from "vite-plugin-environment";

export default async function (config: ConfigEnv): Promise<UserConfig> {
  return {
    plugins: [EnvironmentPlugin(["NODE_ENV"]), sveltekit()],
    ssr: {
      noExternal: ["beercss"],
    },
  };
}
