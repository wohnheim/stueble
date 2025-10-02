import { browser } from "$app/environment";
import { pack, unpack } from "msgpackr";
import { derived, get, readable, writable } from "svelte/store";

import type {
  Config,
  GuestExtern,
  GuestIntern,
  HostOrTutor,
  MessageFromClient,
  MessageFromServer,
  ResponseMap,
  User,
  UserProperties,
} from "$lib/api/types";
import { database } from "$lib/lib/database.svelte";
import { error } from "$lib/lib/error";
import { ui_object } from "$lib/lib/UI.svelte";
import { timeoutPromise } from "$lib/lib/utils";

class HTTPClient {
  /* Auth */

  async login(user: string, password: string) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user,
        password,
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  async createAccount(
    user: UserProperties,
    email: string,
    password: string,
    username: string,
  ) {
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...user,
        email,
        password,
        username,
        privacyPolicy: true,
      }),
    });

    if (res.ok) return true;
    else if (res.status == 400 || Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  async verifyAccount(token: string) {
    const res = await fetch("/api/auth/verify_signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
      }),
    });

    if (res.ok) return true;
    else if (res.status == 400 || Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  async logout(forward = true) {
    const res = await fetch("/api/auth/logout", {
      method: "POST",
    });

    if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    if (browser && res.ok && forward) {
      localStorage.removeItem("loggedIn");
      window.location.href = "/";
    }
  }

  async deleteAccount(forward = true) {
    const res = await fetch("/api/auth/delete", {
      method: "DELETE",
    });

    if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    if (browser && res.ok && forward) {
      localStorage.removeItem("loggedIn");
      window.location.href = "/";
    }
  }

  /* Users */

  async createUser(user: UserProperties) {
    const res = await fetch("/api/user", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...user,
        verified: true,
        privacyPolicy: true,
      }),
    });

    if (res.ok) return await res.json<GuestIntern>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async modifyUser(
    user: (Partial<GuestIntern> | Partial<GuestExtern>) & { id: string },
  ) {
    const res = await fetch("/api/user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(user),
    });

    if (res.ok) return await res.json<GuestIntern | GuestExtern>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async getUser() {
    const res = await fetch("/api/user");

    if (res.ok) return await res.json<User>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async searchUsers(props: Partial<UserProperties & { email: string }>) {
    console.assert(
      props.firstName !== undefined ||
        props.lastName !== undefined ||
        props.roomNumber !== undefined ||
        props.residence !== undefined ||
        props.email !== undefined,
    );

    const params = new URLSearchParams();
    if (props.firstName !== undefined)
      params.append("first_name", props.firstName);
    if (props.lastName !== undefined)
      params.append("last_name", props.lastName);
    if (props.roomNumber !== undefined)
      params.append("room_number", props.roomNumber.toString());
    if (props.residence !== undefined)
      params.append("residence", props.residence);
    if (props.email !== undefined) params.append("email", props.email);

    const res = await fetch("/api/user/search?" + params.toString());

    if (res.ok) return await res.json<User[]>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  /* Guests */

  async getGuestList() {
    const res = await fetch("/api/guests");

    if (res.ok) return await res.json<(GuestIntern | GuestExtern)[]>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async addToGuestList(id?: string, date?: Date) {
    const res = await fetch("/api/guests", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body:
        id !== undefined || date !== undefined
          ? JSON.stringify({
              id,
              date: date?.toISOString(),
            })
          : undefined,
    });

    if (res.ok) return await res.json<GuestIntern | GuestExtern>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async modifyGuest(props: { id: string; present: boolean }) {
    const res = await fetch("/api/guest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(props),
    });

    if (res.ok) return await res.json<GuestIntern | GuestExtern>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async removeFromGuestList(id?: string, date?: Date) {
    const res = await fetch("/api/guests", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body:
        id !== undefined || date !== undefined
          ? JSON.stringify({
              id,
              date: date?.toISOString(),
            })
          : undefined,
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async inviteExtern(
    firstName: string,
    lastName: string,
    email?: string,
    date?: Date,
  ) {
    const res = await fetch("/api/guests/invitee", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firstName,
        lastName,
        email,
        date: date?.toISOString(),
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  /* Hosts */

  async getHosts() {
    const res = await fetch("/api/hosts");

    if (res.ok) return await res.json<HostOrTutor[]>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async addHosts(hosts: string[], date?: Date) {
    const res = await fetch("/api/hosts", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hosts,
        date: date?.toISOString(),
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  async removeHosts(hosts: string[], date?: Date) {
    const res = await fetch("/api/hosts", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hosts,
        date: date?.toISOString(),
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  /* Tutors */

  async getTutors() {
    const res = await fetch("/api/tutors");

    if (res.ok) return await res.json<HostOrTutor[]>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async addTutors(tutors: string[]) {
    const res = await fetch("/api/tutors", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tutors,
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  async removeTutors(tutors: string[]) {
    const res = await fetch("/api/tutors", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tutors,
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  /* Motto */

  async modifyMotto(motto?: string, description?: string, date?: Date) {
    if (motto === undefined && description == undefined) return false;

    const res = await fetch("/api/motto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        motto,
        description,
        date: date?.toISOString(),
      }),
    });

    if (res.ok) return true;
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    return false;
  }

  /* Config */

  async getConfig() {
    const res = await fetch("/api/config");

    if (res.ok) return await res.json<Config>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }

  async modifyConfig(config: Partial<Config>) {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (res.ok) return await res.json<Config>();
    else if (Math.floor(res.status / 100) == 5)
      console.warn("Failure: " + res.json());

    throw new Error(res.status.toString());
  }
}

class WebSocketClient {
  readonly connected = derived(error.error, (error) => error === false);

  private socket: WebSocket;
  private reconnectSeconds: number;
  private messageId: number;
  private promises: {
    resolve: (value: any) => void;
    reject: (reason?: any) => void;
  }[];
  private buffer: Uint8Array[];

  constructor() {
    this.reconnectSeconds = 0;
    this.messageId = 0;
    this.promises = [];
    this.buffer = [];

    this.socket = this.connect();

    this.connected.subscribe((value) => {
      if (!value) {
        for (let i = 0; i < this.promises.length; ++i) {
          const promise = this.promises[i];

          if (promise !== undefined) {
            promise.reject("Connection lost");
            delete this.promises[i];
          }
        }
      }
    });
  }

  private onOpen = () => {
    this.sendBuffered();
  };

  private connect() {
    this.socket = new WebSocket(
      `${browser && location.protocol == "https:" ? "wss:" : "ws:"}//${location.host}/api/websocket`,
    );

    this.socket.binaryType = "arraybuffer";

    this.socket.addEventListener("message", (event) => {
      let data;

      if (this.reconnectSeconds != 0) this.reconnectSeconds = 0;

      if (event.data instanceof ArrayBuffer) {
        data = unpack(new Uint8Array(event.data));
      } else if (typeof event.data == "string") {
        data = JSON.parse(event.data);
      } else {
        console.log(event.data);
        throw new Error("WebSocket: Unknown type.");
      }

      this.handleData(data);
    });

    this.socket.addEventListener("close", (event) => {
      console.log(
        "WebSocket closed" + (event.reason ? ", reason: " + event.reason : "."),
      );

      // Don't reconnect if unauthorized
      const e = get(error.error);
      if (e !== false && e.icon == "warning") return;

      // Higher reconnect interval if request crashed the connection
      const newestPromise = this.promises[this.messageId];
      if (newestPromise !== undefined && this.reconnectSeconds == 0)
        this.reconnectSeconds = 3;

      error
        .disconnected(this.reconnectSeconds > 10 ? 10 : this.reconnectSeconds++)
        .then(undefined, () => this.connect());
    });

    return this.socket;
  }

  private sendBuffered() {
    if (this.socket.readyState !== 1) return;

    let msg;
    while ((msg = this.buffer[0]) !== undefined) {
      this.socket.send(msg);
      this.buffer.splice(0, 1);
    }
  }

  sendMessage<T extends MessageFromClient>(message: T): ResponseMap<T> {
    const msg = Object.hasOwn(message, "resId")
      ? message
      : Object.assign(message, { reqId: ++this.messageId });

    if (this.socket.readyState === 1) {
      this.socket.send(pack(msg));
    } else {
      this.buffer.push(pack(msg));
    }

    if (
      (msg.event == "ping" ||
        msg.event == "requestMotto" ||
        msg.event == "requestQRCode" ||
        msg.event == "requestPublicKey") &&
      "reqId" in message
    ) {
      const msgId = message.reqId as number;

      const promise = new Promise<Awaited<ResponseMap<T>>>((r, j) => {
        this.promises[msgId] = {
          resolve: r,
          reject: j,
        };
      });

      promise.then(
        () => delete this.promises[msgId],
        () => delete this.promises[msgId],
      );

      return promise as any;
    }

    return undefined as ResponseMap<T>;
  }

  checkConnection() {
    const result = Promise.race([
      timeoutPromise(3000),
      this.sendMessage({ event: "ping" }),
    ]);

    return result.then(
      (value) => value === true,
      () => false,
    );
  }

  private handleData(message: MessageFromServer) {
    if (message.event == "status") {
      if (!get(this.connected)) {
        ui_object.capabilities = message.data.capabilities;

        if (message.data.authorized) {
          error.error.set(false);
          this.onOpen();
        } else {
          error.unauthorized();
        }
      }
    } else if (message.event == "stuebleStatus") {
      ui_object.status = {
        ...message.data,
        date: new Date(message.data.date),
        registrationStartsAt: new Date(message.data.date),
      };
    } else if (
      message.event == "guestAdded" ||
      message.event == "guestModified"
    ) {
      if (message.data.extern) database.addGuestExtern(message.data);
      else database.addGuestIntern(message.data);
    } else if (message.event == "guestRemoved") {
      database.deleteGuestExtern(message.data);
      database.deleteGuestInternById(message.data);
    } else if (message.event == "hostAdded") {
      database.addHost(message.data);
    } else if (message.event == "hostRemoved") {
      database.deleteHost(message.data);
    } else if (message.event == "tutorAdded") {
      database.addTutor(message.data);
    } else if (message.event == "tutorRemoved") {
      database.deleteTutor(message.data);
    } else if (message.event == "error") {
      if (message.reqId !== undefined) {
        const promise = this.promises[message.reqId];
        if (promise !== undefined) promise.reject(message.data.message);

        delete this.promises[message.reqId];
      } else {
        console.warn("Error from Server:", message.data);
      }
    } else if ("reqId" in message) {
      const promise = this.promises[message.reqId];
      if (promise !== undefined) promise.resolve(message.data);

      delete this.promises[message.reqId];
    } else {
      console.warn("Error: Type not found, Message:", message);
    }
  }
}

export function apiClient(method: "http"): HTTPClient;
export function apiClient(method: "ws"): WebSocketClient;
export function apiClient(method: "http" | "ws") {
  if (method == "http") {
    return get(httpStore);
  } else {
    let store = get(wsStore);

    if (store === undefined) {
      store = new WebSocketClient();
      wsStore.set(store);
      return store;
    } else {
      return store;
    }
  }
}

const httpStore = readable(new HTTPClient());
const wsStore = writable<WebSocketClient>();
