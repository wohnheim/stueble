<script lang="ts">
  import { browser } from "$app/environment";
  import { onMount, untrack } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { database } from "$lib/lib/database.svelte";
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

  /* Host Data */

  const loadHostDataFromServer = async () => {
    const key = await apiClient("ws").sendMessage({
      event: "requestPublicKey",
    });

    settings.set("publicKey", JSON.stringify(key));
    ui_object.publicKey = await importKey(key);
  };

  const loadHostDataFromDatabase = async () => {
    if (settings.settings["publicKey"])
      ui_object.publicKey = await importKey(
        JSON.parse(settings.settings["publicKey"]),
      );
  };

  /* Admin Data */

  const loadAdminDataFromServer = async () => {
    ui_object.config = await apiClient("http").getConfig();

    settings.set("config", JSON.stringify(ui_object.config));
  };

  const loadAdminDataFromDatabase = async () => {
    if (settings.settings["config"])
      ui_object.config = JSON.parse(settings.settings["config"]);
  };

  let loaded = $state(false);
  let loading = false;

  const loadFromServer = async () => {
    if (localStorage.getItem("loggedIn")) {
      // Initialize IndexedDB mapping
      await settings.init();
      await database.init();

      // Load via WebSocket
      ui_object.user = await apiClient("http").getUser();

      ui_object.qrCodeData = await apiClient("ws").sendMessage({
        event: "requestQRCode",
      });

      ui_object.motto = await apiClient("ws").sendMessage({
        event: "requestMotto",
      });

      // Store in IndexedDB
      await settings.set("user", JSON.stringify(ui_object.user));

      await settings.set("qrCodeData", JSON.stringify(ui_object.qrCodeData));

      await settings.set("motto", ui_object.motto);
    }
  };

  const loadFromDatabase = async () => {
    if (settings.settings["user"])
      ui_object.user = JSON.parse(settings.settings["user"]);

    if (settings.settings["qrCodeData"])
      ui_object.qrCodeData = JSON.parse(settings.settings["qrCodeData"]);

    if (settings.settings["motto"])
      ui_object.motto = settings.settings["motto"];
  };

  onMount(() => {
    if (!loaded && !loading) {
      loading = true;

      loadFromServer()
        .catch(() => {
          loadFromDatabase().finally(() => {
            loaded = true;
            loading = false;
          });
        })
        .then(() => {
          loaded = true;
          loading = false;
        });
    }
  });

  $effect(() => {
    if (browser && loaded) {
      if (ui_object.capabilities.find((c) => c == "host"))
        untrack(() =>
          loadHostDataFromServer().catch(() => loadHostDataFromDatabase()),
        );

      if (ui_object.capabilities.find((c) => c == "admin"))
        untrack(() =>
          loadAdminDataFromServer().catch(() => loadAdminDataFromDatabase()),
        );
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
{:else if ui_object.path.main == "settings"}
  <Settings />
{/if}
