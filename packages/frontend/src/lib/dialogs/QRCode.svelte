<script lang="ts">
  import QRCode from "qrcode";
  import { fade } from "svelte/transition";
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import type { QRCodeData } from "$lib/api/types";
  import { settings } from "$lib/lib/settings.svelte";

  const demoData = JSON.stringify({
    data: {
      id: "1d419481-4fab-4170-acd9-bc20dcbf224a",
      timestamp: 1755567259,
    },
    signature:
      "AFE9E5E6215CB066F60FB8A77E17B5E7874158FD2FB3BA8346C4AC2C65D1E0E827C3EFCBB3A073F9CB5DC5D71648E1B7A41C820D06C6974C1EAAB8276C7BD003",
  } as QRCodeData);

  onMount(async () => {
    settings.set("qrCodeData", demoData);

    /* settings.set(
      "qrCodeData",
      JSON.stringify(
        await apiClient("ws").sendMessage({ event: "requestQRCode" }),
      ),
    ); */
  });
</script>

<p style="font-size: large; margin-bottom: 12px;">Einlass QR-Code</p>

{#if settings.settings["qrCodeData"] === undefined}
  <p>Generating QR code...</p>
{:else}
  {#await QRCode.toDataURL(settings.settings["qrCodeData"])}
    <p>Generating QR code...</p>
  {:then qrCode}
    <p>Zeige diesen QR-Code beim Einlass vor.</p>

    <div id="center-box" class="center-align" in:fade={{ duration: 200 }}>
      <img id="qr-code" src={qrCode} alt="QR Code" draggable="false" />
    </div>
  {:catch}
    <p>Failed to generate QR code.</p>
  {/await}
{/if}

<style>
  #center-box {
    width: 100%;
  }

  #qr-code {
    margin: 15px;
    border-radius: 0.75rem;
  }
</style>
