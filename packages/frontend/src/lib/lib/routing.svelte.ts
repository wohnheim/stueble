import { pushState } from "$app/navigation";
import z from "zod";

export class Routing<ZodRoutes extends z.ZodType> {
  private readonly routes: ZodRoutes;
  private readonly start: z.infer<ZodRoutes>;

  path = $state<z.infer<ZodRoutes>>() as z.infer<ZodRoutes>;

  constructor(routes: ZodRoutes, start: z.infer<ZodRoutes>) {
    this.routes = routes;

    this.start = start;
    this.path = start;
  }

  getPath = (pathU: string, pathStore?: string): z.infer<ZodRoutes> => {
    if (pathU.charAt(0) == "/") pathU = pathU.slice(1);

    const params = pathU.split("/");

    if (params.length != 0 && params[0] != "") {
      const res = this.routes.safeParse({
        main: params[0],
        sub: params.length > 1 ? params[1] : undefined,
      });

      if (res.success) return res.data;
    }

    return this.start;
  };

  changePath = (route: z.infer<ZodRoutes>) => {
    if (
      !route ||
      typeof route != "object" ||
      !("main" in route) ||
      !this.start ||
      typeof this.start != "object" ||
      !("main" in this.start)
    )
      return;

    let url: string;
    if (route.main == this.start.main && !("sub" in route)) {
      url = "/";
    } else {
      url =
        "/" +
        route.main +
        ("sub" in route && route.sub !== undefined ? "/" + route.sub : "");
    }

    pushState(url, {});
    this.path = route;
  };

  pathBackwards = () => {
    if (!this.path || typeof this.path != "object" || !("main" in this.path))
      return;

    pushState("/" + this.path.main, {});
    if ("sub" in this.path) this.path.sub = undefined;
  };
}
