import { openDB, type DBSchema, type IDBPDatabase } from "idb";

interface SettingsDB extends DBSchema {
  settings: {
    value: string;
    key:
      | "motto"
      | "description"
      | "config"
      | "user"
      | "status"
      | "publicKey"
      | "qrCodeData"
      | "welcomeClosed"
      | "guestListFetched"
      | "hostsFetched"
      | "tutorsFetched";
  };
}

class Settings {
  private database: () => IDBPDatabase<SettingsDB>;
  settings = $state<
    Partial<Record<SettingsDB["settings"]["key"], string | undefined>>
  >({});
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

  private get = async (key: SettingsDB["settings"]["key"]) =>
    this.database().get("settings", key);

  set = async (
    key: SettingsDB["settings"]["key"],
    val: SettingsDB["settings"]["value"],
  ) => {
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
