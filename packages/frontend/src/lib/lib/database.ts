import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import { get, writable } from "svelte/store";

import type { GuestExtern, GuestIntern } from "$lib/api/types";

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
}

const database = writable<IDBPDatabase<StuebleDB>>();

const openDatabase = async () => {
  if (get(database) === undefined) {
    const db = await openDB<StuebleDB>("stueble", 1, {
      upgrade(db) {
        /* Guests Intern  */
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
          keyPath: "uuid",
        });

        externStore.createIndex("by-last-name", "lastName", {
          unique: false,
        });
      },
    });

    database.set(db);
    return db;
  } else return get(database);
};

export const clearObjectStores = async () => {
  const db = await openDatabase();

  for (const store of db.objectStoreNames) {
    await db.clear(store);
  }
};

export const deleteGuestIntern = async (
  residence: string,
  roomNumber: number,
) => {
  const db = await openDatabase();

  await db.delete("guestsIntern", IDBKeyRange.only([residence, roomNumber]));
};

export const deleteGuestInternById = async (id: string) => {
  const db = await openDatabase();

  const key = await db.getKeyFromIndex(
    "guestsIntern",
    "by-id",
    IDBKeyRange.only(id),
  );
  if (key != undefined) await db.delete("guestsIntern", key);
};

export const deleteGuestExtern = async (uuid: string) => {
  const db = await openDatabase();

  await db.delete("guestsIntern", uuid);
};

export const addGuestIntern = async (guest: GuestIntern) => {
  const { extern, ...guestWithoutExtern } = guest;

  const db = await openDatabase();

  await db.put("guestsIntern", guestWithoutExtern);
};

export const addGuestExtern = async (guest: GuestExtern) => {
  const { extern, ...guestWithoutExtern } = guest;

  const db = await openDatabase();

  await db.put("guestsExtern", guestWithoutExtern);
};

export const getGuests = async () => {
  const db = await openDatabase();

  const array: (GuestIntern | GuestExtern)[] = (
    await db.getAll("guestsIntern")
  ).map((g) => Object.assign(g, { extern: false }));

  return array.concat(
    (await db.getAll("guestsExtern")).map((g) =>
      Object.assign(g, { extern: true } as { extern: true }),
    ),
  );
};
