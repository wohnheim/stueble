<script lang="ts">
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object, type RouteMain } from "$lib/lib/UI.svelte";

  onMount(async () => {
    // Demo Data
    settings.set(
      "motto",
      "Melde dich gleich für das beste Stüble dieses Semesters an! 🎉\nDas Motto dieser Woche ist “Man in Black”. 🕶️\nSchmeißt euch in Schale, wir freuen uns auf euch!",
    );

    settings.set(
      "motto",
      await apiClient("ws").sendMessage({ event: "requestMotto" }),
    );
  });
</script>

<div id="center-container" class="middle-align center-align">
  <span class="expand"></span>

  <h4 class="no-margin">Willkommen Stüble-Besucher*in!</h4>

  {#if (ui_object.path as RouteMain).sub === undefined}
    <p class="margin-left margin-right">
      {#if settings.settings["motto"]}
        {#each settings.settings["motto"].split("\n") as line}
          {line}<br />
        {/each}
      {:else}
        Melde dich gleich für das beste Stüble dieser Woche an!
      {/if}
    </p>

    <button
      class="top-margin-small"
      onclick={async () => {
        if (ui_object.user !== undefined) {
          const res = await apiClient("http").addToGuestList(ui_object.user.id);

          if (res != null) ui_object.changePath({ main: "main", sub: "invitation" });
        }
      }}
    >
      <i>event</i>
      <span>Anmelden</span>
    </button>

    <span class="expand"></span>
  {:else}
    <p class="margin-left margin-right">
      Auf dieser Seite kannst du dir deinen personalisierten QR-Code anzeigen
      lassen und einen Gast zum nächsten Stüble einladen.
    </p>

    <div>
      <button
        class="top-margin-small"
        onclick={() => ui_object.openDialog({ mode: "qrcode" })}
      >
        <i>qr_code</i>
        <span>QR-Code anzeigen</span>
      </button>
      <button class="top-margin-small secondary">
        <i>person_add</i>
        <span>Gast einladen</span>
      </button>
    </div>

    <span class="expand"></span>

    <button
      class="large-margin"
      onclick={async () => {
        if (ui_object.user !== undefined) {
          const res = await apiClient("http").removeFromGuestList(
            ui_object.user.id,
          );

          if (res != null) ui_object.changePath({ main: "main" });
        }
      }}
    >
      <i>cancel</i>
      <span>Abmelden</span>
    </button>
  {/if}
</div>

<style>
  #center-container {
    height: 100%;
    width: 100%;

    flex-flow: column;
  }

  .expand {
    flex-grow: 1;
  }
</style>
