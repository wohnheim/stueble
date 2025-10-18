import { browser } from "$app/environment";

export type MaybePromise<T> = T | Promise<T>;

export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type Overwrite<T, U> = Omit<T, keyof U> & U;

export const onGuestPage = () =>
  browser && window.location.pathname.slice(0, 6) == "/guest";

export const capitalizeFirstLetter = (str: string) =>
  str.charAt(0).toUpperCase() + str.slice(1);

export const isEmpty = (obj: Object) => {
  for (const prop in obj) {
    if (Object.hasOwn(obj, prop)) {
      return false;
    }
  }

  return true;
};

export function sortAlphabetically<T extends Object>(obj: T) {
  return Object.fromEntries(
    Object.entries(obj).sort(([keyA], [keyB]) => keyA.localeCompare(keyB)),
  ) as T;
}

// Mutates array
export function findAndRemove<T>(
  array: Array<T>,
  find0: Parameters<Array<T>["findIndex"]>[0],
  find1?: Parameters<Array<T>["findIndex"]>[1],
) {
  const index = array.findIndex(find0, find1);
  if (index !== -1) return array.splice(index, 1).at(0);

  return undefined;
}

export const stringToArrayBuffer = (str: string) => {
  return new TextEncoder().encode(str).buffer;
};

export const base64ToArrayBuffer = (signature: string) => {
  return Uint8Array.from(atob(signature), (c) => c.charCodeAt(0)).buffer;
};

export const hexToArrayBuffer = (hex: string) => {
  const octets = hex.match(/.{2}/g);
  if (!octets) throw new Error("Conversion: Invalid hex string");
  return new Uint8Array(octets.map((o) => parseInt(o, 16))).buffer;
};

export const arrayBufferToHex = (buffer: ArrayBuffer) => {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
};

export const blobToArrayBuffer = (blob: Blob) => {
  return new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        if (reader.result instanceof ArrayBuffer) {
          resolve(reader.result);
        } else {
          reject("Conversion: Wrong type");
        }
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = (error) => {
      reject(error);
    };
    reader.readAsArrayBuffer(blob);
  });
};

export const typedArrayToBuffer = (array: Uint8Array) => {
  return array.buffer.slice(
    array.byteOffset,
    array.byteLength + array.byteOffset,
  ) as ArrayBuffer;
};

export const numberToUint8Array = (number: number, length = 4) => {
  const array = new Uint8Array(length);

  for (let i = 0; i < length; i++) {
    array[i] = number % 256;
    number = Math.floor(number / 256);
  }
  if (number % 256 !== 0) throw new Error("Conversion: Number too high.");

  return array;
};

export const uint8ArrayToNumber = (array: Uint8Array) => {
  let number = 0;

  for (let i = array.length - 1; i >= 0; i--) {
    number = number * 256 + array[i]!;
  }

  return number;
};

export const timeoutPromise = (ms: number) =>
  new Promise<void>((_, reject) => setTimeout(() => reject("Timeout"), ms));
