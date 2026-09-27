import type { StuebleStatus } from "./types";

export const parseStuebleStatus = (status: StuebleStatus) => {
  return {
    ...status,
    date: status.date !== undefined ? new Date(status.date) : undefined,
    registrationStartsAt:
      status.registrationStartsAt !== undefined
        ? new Date(status.registrationStartsAt)
        : undefined,
  };
};
