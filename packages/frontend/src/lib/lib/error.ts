import { derived, writable } from "svelte/store";

import { timeoutPromise } from "./utils";
import { ui_object } from "./UI.svelte";

class VisibleError {
  readonly error = writable<false | { icon: string; text: string }>({
    icon: "",
    text: "",
  });

  readonly overlay = derived(this.error, (error) =>
    error === false ? "hidden" : "",
  );

  readonly snackbarError = writable<false | { icon?: string; text: string }>({
    text: "",
  });

  solved = () => {
    this.error.set(false);
  };

  offline = () => {
    this.error.set({
      icon: "cloud_off",
      text: "Offline, bitte verbinde Dich mit dem Internet.",
    });
  };

  unauthorized = () => {
    this.error.set({
      icon: "warning",
      text: "Unerlaubter Zugriff, Weiterleitung zur Einrichtung.",
    });

    setTimeout(() => (location.href = "/setup"), 2000);
  };

  disconnected = (seconds: number) => {
    this.error.set({
      icon: "sync_problem",
      text: `Getrennt, erneuter Versuch${seconds == 0 ? "" : ` in ${seconds} Sekunden`}.`,
    });

    return timeoutPromise(seconds * 1000);
  };

  snackbar = (text: string, icon?: string, seconds = 10) => {
    this.snackbarError.set({ icon, text });
    ui(ui_object.snackbarElement, seconds * 1000);
  };
}

export const error = new VisibleError();
