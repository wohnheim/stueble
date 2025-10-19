import { openDB, type DBSchema, type IDBPDatabase, type StoreNames } from "idb";

import type {
  GuestExtern,
  GuestIntern,
  HostOrTutor,
  UserProperties,
} from "$lib/api/types";

/* Buffered actions */

interface ActionCommon {
  timestamp: number;
}

export interface CreateUserAction {
  action: "createUser";
  data: UserProperties;
}

export interface ModifyUserAction {
  action: "modifyUser";
  data: (Partial<GuestIntern> | Partial<GuestExtern>) & { id: string };
}

export interface AddToGuestListAction {
  action: "addToGuestList";
  data?: { id?: string; date: Date } | { id: string; date?: Date };
}

export interface ModifyGuestAction {
  action: "modifyGuest";
  data: { id: string; present: boolean };
}

export interface RemoveFromGuestListAction {
  action: "removeFromGuestList";
  data?: { id?: string; date: Date } | { id: string; date?: Date };
}

/* Database */

interface StuebleDB extends DBSchema {
  guestsIntern: {
    value: Omit<GuestIntern, "extern">;
    key: string;
    indexes: {
      "by-room-number": number;
      "by-last-name": string;
      "by-id": string;
    };
  };
  guestsExtern: {
    value: Omit<GuestExtern, "extern">;
    key: string;
    indexes: { "by-last-name": string };
  };
  hosts: {
    value: HostOrTutor;
    key: string;
    indexes: { "by-last-name": string };
  };
  tutors: {
    value: HostOrTutor;
    key: string;
    indexes: { "by-last-name": string };
  };
  buffer: {
    value: ActionCommon &
      (
        | CreateUserAction
        | ModifyUserAction
        | AddToGuestListAction
        | ModifyGuestAction
        | RemoveFromGuestListAction
      );
    key: number;
    indexes: { "by-action": string };
  };
}

class Database {
  private database: () => IDBPDatabase<StuebleDB>;
  ready = $state(false);

  guests = $state<(GuestIntern | GuestExtern)[]>([]);
  hosts = $state<StuebleDB["hosts"]["value"][]>([]);
  tutors = $state<StuebleDB["tutors"]["value"][]>([]);

  buffer = $state<{
    [index: number]: StuebleDB["buffer"]["value"] | undefined;
  }>({});

  constructor() {
    this.database = () => {
      throw new Error("Database not initialized");
    };
  }

  init = async () => {
    const db = await this.openDatabase();
    this.database = () => db;

    await this.getAll();
    this.ready = true;
  };

  async clear(stores?: StoreNames<StuebleDB>[]) {
    for (const store of stores ?? this.database().objectStoreNames) {
      await this.database().clear(store);

      if (store == "guestsIntern" || store == "guestsExtern")
        this.guests.splice(0, this.guests.length);
      else if (Array.isArray(this[store]))
        this[store].splice(0, this[store].length);
      else this[store] = {} as any;
    }
  }

  private openDatabase = () =>
    openDB<StuebleDB>("stueble", 2, {
      upgrade(db) {
        /* Guests Intern */
        const internStore = db.createObjectStore("guestsIntern", {
          keyPath: ["residence", "roomNumber"],
        });

        internStore.createIndex("by-room-number", "roomNumber", {
          unique: false,
        });
        internStore.createIndex("by-last-name", "lastName", {
          unique: false,
        });
        internStore.createIndex("by-id", "id", {
          unique: false,
        });

        /* Guests Extern */
        const externStore = db.createObjectStore("guestsExtern", {
          keyPath: "id",
        });

        externStore.createIndex("by-last-name", "lastName", {
          unique: false,
        });

        /* Hosts */
        const hostsStore = db.createObjectStore("hosts", {
          keyPath: "id",
        });

        hostsStore.createIndex("by-last-name", "lastName", {
          unique: false,
        });

        /* Tutors */
        const tutorsStore = db.createObjectStore("tutors", {
          keyPath: "id",
        });

        tutorsStore.createIndex("by-last-name", "lastName", {
          unique: false,
        });

        /* Buffer */
        const bufferStore = db.createObjectStore("buffer", {
          keyPath: "id",
          autoIncrement: true,
        });

        bufferStore.createIndex("by-action", "action", {
          unique: false,
        });
      },
    });

  private getAll = async () => {
    const array: (GuestIntern | GuestExtern)[] = (
      await this.database().getAll("guestsIntern")
    ).map((g) => Object.assign(g, { extern: false } as { extern: false }));

    this.guests = array.concat(
      (await this.database().getAll("guestsExtern")).map((g) =>
        Object.assign(g, { extern: true } as { extern: true }),
      ),
    );

    this.hosts = await this.database().getAll("hosts");
    this.tutors = await this.database().getAll("tutors");

    this.buffer = await this.database().getAll("buffer");
  };

  /* Guests */

  deleteGuestIntern = async (residence: string, roomNumber: number) => {
    await this.database().delete(
      "guestsIntern",
      IDBKeyRange.only([residence, roomNumber]),
    );

    const index = this.guests.findIndex(
      (g) =>
        !g.extern && g.residence == residence && g.roomNumber == roomNumber,
    );
    if (index != -1) this.guests.splice(index, 1);
  };

  deleteGuestInternById = async (id: string) => {
    const key = await this.database().getKeyFromIndex(
      "guestsIntern",
      "by-id",
      IDBKeyRange.only(id),
    );
    if (key != undefined) await this.database().delete("guestsIntern", key);

    const index = this.guests.findIndex((g) => g.id == id);
    if (index != -1) this.guests.splice(index, 1);
  };

  deleteGuestExtern = async (id: string) => {
    await this.database().delete("guestsIntern", id);

    const index = this.guests.findIndex((g) => g.id == id);
    if (index != -1) this.guests.splice(index, 1);
  };

  addGuestIntern = async (guest: GuestIntern) => {
    const { extern, ...guestWithoutExtern } = guest;

    await this.database().put("guestsIntern", guestWithoutExtern);

    const index = this.guests.findIndex((g) => guest.id == g.id);
    if (index !== -1) this.guests.splice(index, 1);

    this.guests.push(guest);
  };

  addGuestExtern = async (guest: GuestExtern) => {
    const { extern, ...guestWithoutExtern } = guest;

    await this.database().put("guestsExtern", guestWithoutExtern);

    const index = this.guests.findIndex((g) => guest.id == g.id);
    if (index !== -1) this.guests.splice(index, 1);

    this.guests.push(guest);
  };

  addGuests = async (guests: (GuestIntern | GuestExtern)[]) => {
    for (const guest of guests) {
      if (guest.extern) this.addGuestExtern(guest);
      else this.addGuestIntern(guest);
    }
  };

  /* Hosts */

  addHost = async (host: HostOrTutor) => {
    await this.database().put("hosts", host);

    const index = this.hosts.findIndex((h) => host.id == h.id);
    if (index !== -1) this.hosts.splice(index, 1);

    this.hosts.push(host);
  };

  addHosts = async (hosts: HostOrTutor[]) => {
    for (const host of hosts) {
      await this.addHost(host);
    }
  };

  deleteHost = async (id: string) => {
    await this.database().delete("hosts", id);

    const index = this.hosts.findIndex((h) => h.id == id);
    if (index != -1) this.hosts.splice(index, 1);
  };

  deleteHosts = async (ids: string[]) => {
    for (const id of ids) {
      await this.deleteHost(id);
    }
  };

  /* Tutors */

  addTutor = async (tutor: HostOrTutor) => {
    await this.database().put("tutors", tutor);

    const index = this.tutors.findIndex((t) => tutor.id == t.id);
    if (index !== -1) this.tutors.splice(index, 1);

    this.tutors.push(tutor);
  };

  addTutors = async (tutors: HostOrTutor[]) => {
    for (const tutor of tutors) {
      await this.addTutor(tutor);
    }
  };

  deleteTutor = async (id: string) => {
    await this.database().delete("tutors", id);

    const index = this.tutors.findIndex((t) => t.id == id);
    if (index != -1) this.tutors.splice(index, 1);
  };

  deleteTutors = async (ids: string[]) => {
    for (const id of ids) {
      await this.deleteTutor(id);
    }
  };

  /* Buffered actions */

  addToBuffer = async (
    item: Omit<StuebleDB["buffer"]["value"], "timestamp" | "id">,
  ) => {
    const timestamped = Object.assign(item, {
      timestamp: Date.now() / 1000,
    }) as StuebleDB["buffer"]["value"];

    const key = await this.database().put("buffer", timestamped);
    this.buffer[key] = timestamped;
  };

  private deleteFromBuffer = async (id: number) => {
    await this.database().delete("buffer", id);
    delete this.buffer[id];
  };

  bufferIteration = async (
    remove: (item: StuebleDB["buffer"]["value"]) => Promise<boolean>,
  ) => {
    for (const [key, value] of Object.entries(this.buffer)) {
      if (value === undefined) continue;

      try {
        await remove(value);

        this.deleteFromBuffer(Number(key));
      } catch (e: any) {
        return false;
      }
    }

    return true;
  };
}

export const database = new Database();
