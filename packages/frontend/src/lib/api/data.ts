import type { StuebleStatus } from "./types";

export const parseStuebleStatus = (status: StuebleStatus) => {
  return {
    ...status,
    date: new Date(status.date),
    registrationStartsAt:
      status.registrationStartsAt !== undefined
        ? new Date(status.registrationStartsAt)
        : undefined,
  };
};
