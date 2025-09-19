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
      text: "Offline, please connect to the internet.",
    });
  };

  unauthorized = () => {
    console.log("Unauthorized");
    this.error.set({
      icon: "warning",
      text: "Unauthorized, forwarding to setup.",
    });

    setTimeout(() => (location.href = "/setup"), 2000);
  };

  disconnected = (seconds: number) => {
    console.log("Disconnected");
    this.error.set({
      icon: "sync_problem",
      text: `Disconnected, retrying ${seconds == 0 ? "now" : `in ${seconds} seconds`}.`,
    });

    return timeoutPromise(seconds * 1000);
  };
}

export const error = new VisibleError();
