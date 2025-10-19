import ui from "beercss";
import z from "zod";

import type {
  Capabilities,
  Config,
  GuestExtern,
  GuestIntern,
  QRCodeData,
  StuebleStatus as StuebleStatusUnparsed,
  User,
} from "$lib/api/types";
import type { Overwrite } from "$lib/lib/utils";
import { Routing } from "$lib/lib/routing.svelte";

/* Site navigation */

const routesTop = z.object({
  main: z.enum(["credits"]),
});

const routeMain = z.object({
  main: z.enum(["start"]),
  sub: z.enum(["einladen"]).optional(),
});

export type RouteMain = z.infer<typeof routeMain>;

const routeHost = z.object({
  main: z.enum(["wirte"]),
  sub: z.enum(["liste"]).optional(),
});

export type RouteHost = z.infer<typeof routeHost>;

const routeSettings = z.object({
  main: z.enum(["einstellungen"]),
  sub: z.enum(["wirte", "tutoren"]).optional(),
});

export type RouteSettings = z.infer<typeof routeSettings>;

const routes = z.union([routesTop, routeMain, routeHost, routeSettings]);

export type Routes = z.infer<typeof routes>;

/* Student residence mapping */
export enum WohnheimType {
  Altbau = "altbau",
  Anbau = "anbau",
  Neubau = "neubau",
  Hirte = "hirte",
}

/* Parsed API types */
export type StuebleStatus = Overwrite<
  StuebleStatusUnparsed,
  {
    date: Date;
    registrationStartsAt?: Date;
  }
>;

/* Global UI state */

class UI {
  // Window
  height = $state(0);
  width = $state(0);
  layout = $derived<"mobile" | "desktop">(
    this.width < 840 ? "mobile" : "desktop",
  );

  // Service worker
  registration = $state<ServiceWorkerRegistration>();

  // API Capabilities
  capabilities = $state<Capabilities>([]);

  // Navigation
  routing = new Routing(routes, { main: "start" });

  // Persistent properties (using IndexedDB)
  publicKey = $state<CryptoKey>();
  qrCodeData = $state<QRCodeData>();
  config = $state<Config>();
  status = $state<StuebleStatus>();

  // Personal infos (mutable)
  userParams = $state<
    Overwrite<
      Omit<Omit<User, "id">, "verified"> & {
        email: string;
        password: string;
        username: string;
      },
      {
        roomNumber: number | "";
        residence: User["residence"] | "";
      }
    >
  >({
    firstName: "",
    lastName: "",
    roomNumber: "",
    residence: "",
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

  // Snackbar
  snackbarElement = $state<HTMLDivElement>();

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

        const success = this.dialogProperties?.success || false;
        setTimeout(() => resolve(success), 400);
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

        if (this.dialogProperties?.mode == "edit") {
          const value = this.dialogProperties.value;
          setTimeout(() => resolve(value), 400);
        } else reject("UI: Wrong dialog mode");
      };

      this.generalDialog?.addEventListener("close", onClose);
      ui(this.generalDialog);
    });
  };
}

/* Dialog types */
export interface DialogWelcome {
  mode: "welcome";
}

export interface DialogConfirm {
  mode: "confirm";

  title: string;
  description?: string;
  confirm?: string;
  cancel?: string;
}

export interface DialogEdit {
  mode: "edit";

  title: string;
  description?: string;
  value: string;

  length?: number;
  placeholder?: string;
  type: "string" | "textarea" | "number" | "qrcode";
}

export interface DialogCheckIn {
  mode: "check-in";

  guest: GuestExtern | GuestIntern;
}

export type DialogProperties = (
  | DialogConfirm
  | DialogEdit
  | DialogCheckIn
  | {
      mode: "welcome" | "qrcode" | "unselected";
    }
) & { success?: boolean };

export const ui_object = new UI();
