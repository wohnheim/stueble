import { z } from "zod";

function constant<T extends string>(...t: [T, ...T[]]) {
  return z.enum(t);
}

/* Schemes */

// UUID conforming to RFC4122
export const uuid = z.uuidv4();

export const userProperties = z.object({
  firstName: z.string(),
  lastName: z.string(),
  roomNumber: z.uint32(),
  residence: constant("hirte", "altbau", "anbau", "neubau"),
});

export type UserProperties = z.infer<typeof userProperties>;

export const user = z.object({
  ...userProperties.shape,
  id: uuid,
  verified: z.boolean(),
});

export type User = z.infer<typeof user>;

export const guestIntern = z.object({
  ...user.shape,
  present: z.boolean(),
  extern: z.literal(false),
});

export type GuestIntern = z.infer<typeof guestIntern>;

export const guestExtern = z.object({
  id: uuid,
  firstName: z.string(),
  lastName: z.string(),
  present: z.boolean(),
  extern: z.literal(true),
});

export type GuestExtern = z.infer<typeof guestExtern>;

export const config = z.object({
  maximumGuests: z.int32(),
  sessionExpirationDays: z.int32(),
  maximumInvitesPerUser: z.int32(),
  resetCodeExpirationMinutes: z.int32(),
  qrCodeExpirationMinutes: z.int32(),
});

export type Config = z.infer<typeof config>;

// Message IDs
export const reqId = z.uint32();
export const resId = z.uint32();

/* Operation: receiveStatus */

export const status = z.object({
  event: constant("status"),
  data: z.object({
    authorized: z.boolean(),
    capabilities: z.array(constant("host", "tutor", "admin")),
  }),
  // reqId,
});

export type Capabilities = z.infer<typeof status>["data"]["capabilities"];

/* Operation: sendPing */

export const ping = z.object({
  event: constant("ping"),
  // reqId,
});

export const pong = z.object({
  event: constant("pong"),
  reqId,
  data: z.literal(true),
});

/* Operation: sendHeartbeat */

export const heartbeat = z.object({
  event: constant("heartbeat"),
  // reqId,
});

/* Operation: receiveGuestListChanges */

export const guestAdded = z.object({
  event: constant("guestAdded"),
  resId,
  data: guestIntern.or(guestExtern),
});

export const guestRemoved = z.object({
  event: constant("guestRemoved"),
  resId,
  data: z.string(),
});

export const guestModified = z.object({
  event: constant("guestModified"),
  resId,
  data: guestIntern.or(guestExtern),
});

export const acknowledgment = z.object({
  event: constant("acknowledgment"),
  resId,
});

/* Operation: requestMotto */

export const requestMotto = z.object({
  event: constant("requestMotto"),
  // reqId,
});

export const motto = z.object({
  event: constant("motto"),
  reqId,
  data: z.string(),
});

/* Operation: requestQRCode */

export const requestQRCode = z.object({
  event: constant("requestQRCode"),
  // reqId,
});

export const qrCode = z.object({
  event: constant("qrCode"),
  reqId,
  data: z.object({
    data: z.object({
      id: uuid,
      timestamp: z.uint32(),
    }),
    signature: z.string(),
  }),
});

export type QRCodeData = z.infer<typeof qrCode>["data"];

/* Operation: requestPublicKey */

export const requestPublicKey = z.object({
  event: constant("requestPublicKey"),
  // reqId,
});

const rsaOtherPrimesInfo = z.object({
  d: z.string().optional(),
  r: z.string().optional(),
  t: z.string().optional(),
});

const jsonWebKey = z.object({
  alg: z.string().optional(),
  crv: z.string().optional(),
  d: z.string().optional(),
  dp: z.string().optional(),
  dq: z.string().optional(),
  e: z.string().optional(),
  ext: z.boolean().optional(),
  k: z.string().optional(),
  key_ops: z.array(z.string()).optional(),
  kty: z.string().optional(),
  n: z.string().optional(),
  oth: z.array(rsaOtherPrimesInfo).optional(),
  p: z.string().optional(),
  q: z.string().optional(),
  qi: z.string().optional(),
  use: z.string().optional(),
  x: z.string().optional(),
  y: z.string().optional(),
});

export const publicKey = z.object({
  event: constant("publicKey"),
  reqId,
  data: jsonWebKey,
});

/* Generic error */

export const error = z.object({
  event: constant("error"),
  reqId: reqId.optional(),
  data: z.object({
    code: z.string(),
    message: z.string(),
  }),
});

/* Messages from client */

export const messageFromClient = z.union([
  ping,
  heartbeat,
  acknowledgment,
  requestMotto,
  requestQRCode,
  requestPublicKey,
]);

export type MessageFromClient = z.infer<typeof messageFromClient>;

/* Messages from server */

export const messageFromServer = z.union([
  status,
  pong,
  guestAdded,
  guestRemoved,
  guestModified,
  motto,
  qrCode,
  publicKey,
  error,
]);

export type MessageFromServer = z.infer<typeof messageFromServer>;

/* Response map */

export type ResponseMap<T> =
  T extends z.infer<typeof ping>
    ? Promise<z.infer<typeof pong>["data"]>
    : T extends z.infer<typeof requestMotto>
      ? Promise<z.infer<typeof motto>["data"]>
      : T extends z.infer<typeof requestQRCode>
        ? Promise<z.infer<typeof qrCode>["data"]>
        : T extends z.infer<typeof requestPublicKey>
          ? Promise<z.infer<typeof publicKey>["data"]>
          : undefined;
