<script lang="ts">
  import { browser } from "$app/environment";
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { getGuests } from "$lib/lib/database";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Home from "$lib/pages/Home.svelte";
  import Guests from "$lib/pages/Guests.svelte";
  import Settings from "$lib/pages/Settings.svelte";
  import Invite from "$lib/pages/Invite.svelte";

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      // Close dialog, cancel selection, etc.
      ui_object.closeDialog();
    } else if (event.key === "Enter") {
      // Submit selection (if valid value), etc.
      if (ui_object.dialogProperties.mode == "check-in") {
        ui_object.closeDialog(true);
      }
    }
  };

  const importKey = (key: JsonWebKey) => {
    return window.crypto.subtle.importKey(
      "jwk",
      key,
      { name: "Ed25519" },
      false,
      ["verify"],
    );
  };

  let loaded = $state(false);
  let loading = false;
  const onLoading = async () => {
    if (localStorage.getItem("loggedIn")) {
      // Load from IndexedDB
      if (settings.settings["motto"])
        ui_object.motto = settings.settings["motto"];

      if (settings.settings["publicKey"])
        ui_object.publicKey = await importKey(
          JSON.parse(settings.settings["publicKey"]),
        );

      if (settings.settings["qrCodeData"])
        ui_object.qrCodeData = JSON.parse(settings.settings["qrCodeData"]);

      // ui_object.guests = await getGuests();

      // Setup WebSocket connection
      // await apiClient("ws").sendMessage({ event: "ping" });
    }
  };

  onMount(() => {
    if (!loaded && !loading) {
      loading = true;
      onLoading().finally(() => {
        loaded = true;
        loading = false;
      });
    }
  });

  $effect(() => {
    if (
      false &&
      browser &&
      loaded &&
      ui_object.capabilities.find((c) => c == "host")
    ) {
      apiClient("ws")
        .sendMessage({ event: "requestPublicKey" })
        .then(async (key) => {
          settings.set("publicKey", JSON.stringify(key));

          ui_object.publicKey = await importKey(key);
          // Possibly infinite loop
        });
    }
  });
</script>

<svelte:window
  bind:innerHeight={ui_object.height}
  bind:innerWidth={ui_object.width}
  on:dragover|preventDefault
  on:keydown={handleKeyDown}
/>

{#if ui_object.path.main == "main"}
  {#if ui_object.path.sub === undefined}
    <Home />
  {:else}
    <Invite />
  {/if}
{:else if ui_object.path.main == "host"}
  <Guests />
{:else if ui_object.path.main == "admin"}
  <Settings />
{/if}
