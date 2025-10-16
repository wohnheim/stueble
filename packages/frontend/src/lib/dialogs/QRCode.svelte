<script lang="ts">
  import QRCode from "qrcode";
  import { fade } from "svelte/transition";
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";

  onMount(
    async () =>
      !settings.settings["qrCodeData"] &&
      settings.set(
        "qrCodeData",
        JSON.stringify(
          await apiClient("ws").sendMessage({ event: "requestQRCode" }),
        ),
      ),
  );
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
