import { openDB, type DBSchema, type IDBPDatabase } from "idb";

interface SettingsDB extends DBSchema {
  settings: {
    value: string;
    key: string;
  };
}

class Settings {
  private database: () => IDBPDatabase<SettingsDB>;
  settings = $state<{ [index: string]: string | undefined }>({});
  ready = $state(false);

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

  private openDatabase = () =>
    openDB<SettingsDB>("settings-store", 1, {
      upgrade(db) {
        db.createObjectStore("settings");
      },
    });

  private get = async (key: string) => this.database().get("settings", key);

  set = async (key: string, val: string) => {
    await this.database().put("settings", val, key);
    this.settings[key] = val;
  };

  clear = async () => this.database().clear("settings");

  private keys = async () => this.database().getAllKeys("settings");

  private getAll = async () => {
    const keys = await this.keys();

    for (const key of keys) {
      const val = await this.get(key);
      if (val !== undefined) this.settings[key] = val;
    }
  };
}

export const settings = new Settings();
