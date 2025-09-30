<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  let extended = $state(false);
</script>

<div id="center-container" class="middle-align center-align">
  <span class="expand"></span>

  <h4 class="no-margin">Willkommen Stüble-Besucher*in!</h4>

  <p>
    Das Motto am {ui_object.status?.date.toLocaleDateString("de-DE")} lautet:
  </p>

  <h5>{settings.settings["motto"]}</h5>

  {#if !extended}
    <div class="row margin-left margin-right">
      <p>{settings.settings["description"]?.split(" ", 7).join(" ")}</p>
      <button class="chip fill round" onclick={() => (extended = true)}>
        ...
      </button>
    </div>
  {:else if settings.settings["description"] !== undefined}
    <p class="margin-left margin-right">
      {#each settings.settings["description"]?.split("\n") as line}
        {line}<br />
      {/each}
    </p>
  {/if}

  {#if !ui_object.status?.registered}
    {#if ui_object.status !== undefined && (ui_object.status.registrationStartsAt === undefined || ui_object.status.registrationStartsAt <= new Date())}
      <button
        class="top-margin-small"
        onclick={() => apiClient("http").addToGuestList()}
      >
        <i>event</i>
        <span>Anmelden</span>
      </button>
    {/if}

    <span class="expand"></span>
  {:else}
    <p class="bold">Du bist angemeldet!</p>

    <div>
      <button
        class="top-margin-small"
        onclick={() => ui_object.openDialog({ mode: "qrcode" })}
      >
        <i>qr_code</i>
        <span>QR-Code anzeigen</span>
      </button>
      <button
        class="top-margin-small secondary"
        onclick={() =>
          ui_object.changePath({ main: "main", sub: "invitation" })}
      >
        <i>person_add</i>
        <span>Externer Gast</span>
      </button>
    </div>

    <span class="expand"></span>

    {#if ui_object.status !== undefined && !ui_object.status.present}
      <button
        class="large-margin"
        onclick={() => apiClient("http").removeFromGuestList()}
      >
        <i>cancel</i>
        <span>Abmelden</span>
      </button>
    {/if}
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
