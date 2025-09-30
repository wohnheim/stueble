import { derived, writable } from "svelte/store";

import { timeoutPromise } from "./utils";

class VisibleError {
  readonly error = writable<false | { icon: string; text: string }>({
    icon: "",
    text: "",
  });

  readonly overlay = derived(this.error, (error) =>
    error === false ? "hidden" : "",
  );

  solved = () => {
    console.log("Error solved");
    this.error.set(false);
  };

  offline = () => {
    console.log("Offline");
    this.error.set({
      icon: "cloud_off",
      text: "Offline, bitte verbinde Dich mit dem Internet.",
    });
  };

  unauthorized = () => {
    console.log("Unauthorized");
    this.error.set({
      icon: "warning",
      text: "Unerlaubter Zugriff, Weiterleitung zur Einrichtung.",
    });

    setTimeout(() => (location.href = "/setup"), 2000);
  };

  disconnected = (seconds: number) => {
    console.log("Disconnected");
    this.error.set({
      icon: "sync_problem",
      text: `Getrennt, erneuter Versuch${seconds == 0 ? "" : ` in ${seconds} Sekunden`}.`,
    });

    return timeoutPromise(seconds * 1000);
  };
}

export const error = new VisibleError();
