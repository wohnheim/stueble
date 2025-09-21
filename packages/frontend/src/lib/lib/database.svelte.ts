import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import type { GuestExtern, GuestIntern, Host } from "$lib/api/types";

interface StuebleDB extends DBSchema {
  guestsIntern: {
    value: Omit<GuestIntern, "extern">;
    key: string;
    indexes: {
      "by-room-number": number;
      "by-last-name": number;
      "by-id": number;
    };
  };
  guestsExtern: {
    value: Omit<GuestExtern, "extern">;
    key: string;
    indexes: { "by-last-name": number };
  };
  hosts: {
    value: Host;
    key: string;
    indexes: { "by-last-name": number };
  };
}

class Database {
  private database: () => IDBPDatabase<StuebleDB>;
  ready = $state(false);

  guests = $state<(GuestIntern | GuestExtern)[]>([]);
  hosts = $state<Host[]>([]);

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

  clear = async () => {
    for (const store of this.database().objectStoreNames) {
      await this.database().clear(store);
    }
  };

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
      },
    });

  private getAll = async () => {
    const array: (GuestIntern | GuestExtern)[] = (
      await this.database().getAll("guestsIntern")
    ).map((g) => Object.assign(g, { extern: false }));

    this.guests = array.concat(
      (await this.database().getAll("guestsExtern")).map((g) =>
        Object.assign(g, { extern: true } as { extern: true }),
      ),
    );

    this.hosts = await this.database().getAll("hosts");
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

    this.guests.push(guest);
  };

  addGuestExtern = async (guest: GuestExtern) => {
    const { extern, ...guestWithoutExtern } = guest;

    await this.database().put("guestsExtern", guestWithoutExtern);

    this.guests.push(guest);
  };

  /* Hosts */

  addHost = async (host: Host) => {
    await this.database().put("hosts", host);

    this.hosts.push(host);
  };

  deleteHost = async (id: string) => {
    await this.database().delete("hosts", id);

    const index = this.hosts.findIndex((h) => h.id == id);
    if (index != -1) this.hosts.splice(index, 1);
  };
}

export const database = new Database();
