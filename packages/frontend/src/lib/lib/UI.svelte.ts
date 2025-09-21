import { pushState } from "$app/navigation";
import ui from "beercss";
import z from "zod";

import type {
  Capabilities,
  Config,
  GuestExtern,
  GuestIntern,
  QRCodeData,
  User,
} from "$lib/api/types";

/* Site navigation */

const routesTop = z.object({
  main: z.enum([]),
});

const routeMain = z.object({
  main: z.enum(["main"]),
  sub: z.enum(["invitation"]).optional(),
});

export type RouteMain = z.infer<typeof routeMain>;

const routeHost = z.object({
  main: z.enum(["host"]),
  sub: z.enum(["list"]).optional(),
});

export type RouteHost = z.infer<typeof routeHost>;

const routeSettings = z.object({
  main: z.enum(["settings"]),
  sub: z.enum(["hosts"]).optional(),
});

export type RouteSettings = z.infer<typeof routeSettings>;

const routes = z.union([routesTop, routeMain, routeHost, routeSettings]);

export type Routes = z.infer<typeof routes>;

/* Student residence mapping */
export enum WohnheimType {
  Hirte = "hirte",
  Altbau = "altbau",
  Anbau = "anbau",
  Neubau = "neubau",
}

/* Global UI state */

class UI {
  // Window
  height = $state(0);
  width = $state(0);
  layout = $derived(this.width < 840 ? "mobile" : "desktop");

  // API Capabilities
  capabilities = $state<Capabilities>([]);

  // Navigation
  path = $state<Routes>({ main: "main" });

  // Config
  config = $state<Config>({
    maximumGuests: 150,
    sessionExpirationDays: 0,
    maximumInvitesPerUser: 0,
    resetCodeExpirationMinutes: 0,
    qrCodeExpirationMinutes: 0,
  });

  // Persistent properties (using IndexedDB)
  motto = $state("");
  publicKey = $state<CryptoKey>();
  qrCodeData = $state<QRCodeData>();

  // Personal infos (mutable)
  userParams = $state<
    Omit<Omit<User, "id">, "verified"> & {
      email: string;
      password: string;
      username: string;
    }
  >({
    firstName: "",
    lastName: "",
    roomNumber: 0,
    residence: "hirte",
    email: "",
    password: "",
    username: "",
  });

  // User
  user = $state<User>();

  // Dialogs
  menuDialog = $state<HTMLDialogElement>();
  generalDialog = $state<HTMLDialogElement>();
  largeDialog = $state<HTMLDialogElement>();

  dialogProperties = $state<DialogProperties>({
    mode: "unselected",
  });

  groupProperties = $state<
    | {
        mode: "properties";
        gid: number;
      }
    | {
        mode: "create";
      }
  >({ mode: "create" });

  // String utils
  returnSubstring = (name: string, length: number) => {
    const position = name.lastIndexOf(".");

    if (name.length <= length) return name;

    if (position !== -1) {
      const end = name.slice(position);

      return name.slice(0, length - 1 - end.length) + end;
    } else {
      return name.slice(0, length - 1);
    }
  };

  /* Dialogs */

  openLargeDialog = async () => {
    ui(this.largeDialog);
  };

  closeDialog = async (success?: boolean) => {
    if (this.generalDialog?.open) {
      if (this.dialogProperties !== undefined) {
        this.dialogProperties.success = success;
      }

      await new Promise<void>((resolve) => {
        ui(this.generalDialog);

        setTimeout(() => resolve(), 400); // BeerCSS: --speed3 + 0.1s
      });
    }
  };

  openDialog = async (properties: DialogProperties) => {
    await this.closeDialog();

    this.dialogProperties = properties;

    return new Promise<boolean>((resolve) => {
      const onClose = () => {
        this.generalDialog?.removeEventListener("close", onClose);

        resolve(this.dialogProperties?.success || false);
      };

      this.generalDialog?.addEventListener("close", onClose);
      ui(this.generalDialog);
    });
  };

  openEditDialog = async (
    properties: Omit<Omit<DialogEdit, "mode">, "value">,
    value = "",
  ) => {
    await this.closeDialog();

    this.dialogProperties = {
      mode: "edit",
      value,
      ...properties,
    };

    return new Promise<string>((resolve, reject) => {
      const onClose = () => {
        this.generalDialog?.removeEventListener("close", onClose);

        if (this.dialogProperties?.mode == "edit")
          resolve(this.dialogProperties.value);
        else reject("UI: Wrong dialog mode");
      };

      this.generalDialog?.addEventListener("close", onClose);
      ui(this.generalDialog);
    });
  };

  /* Path */

  getPath = (pathU: string, pathStore?: string): Routes => {
    if (pathU.charAt(0) == "/") pathU = pathU.slice(1);

    const params = pathU.split("/");

    if (params.length != 0 && params[0] != "") {
      const res = routes.safeParse({
        main: params[0],
        sub: params.length > 1 ? params[1] : undefined,
      });

      if (res.success) return res.data;
    }

    return { main: "main" };
  };

  changePath = (route: Routes) => {
    let url: string;
    if (route.main == "main") {
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
    pushState("/" + this.path.main, {});
    if ("sub" in this.path) this.path.sub = undefined;
  };
}

/* Dialog types */
export interface DialogEdit {
  mode: "edit";

  title: string;
  value: string;

  length?: number;
  placeholder?: string;
  type: "string" | "number" | "qrcode";
}

export interface DialogCheckIn {
  mode: "check-in";

  guest: GuestExtern | GuestIntern;
}

export type DialogProperties = (
  | DialogEdit
  | DialogCheckIn
  | {
      mode: "delete" | "qrcode" | "unselected";
    }
) & { success?: boolean };

export const ui_object = new UI();
