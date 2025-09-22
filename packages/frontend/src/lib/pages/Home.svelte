<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

<div id="center-container" class="middle-align center-align">
  <span class="expand"></span>

  <h4 class="no-margin">Willkommen Stüble-Besucher*in!</h4>

  {#if !ui_object.status?.registered}
    <p class="margin-left margin-right">
      {#if settings.settings["motto"]}
        {#each settings.settings["motto"].split("\n") as line}
          {line}<br />
        {/each}
      {:else}
        Melde dich gleich für das beste Stüble dieser Woche an!
      {/if}
    </p>

    {#if ui_object.status !== undefined && ui_object.status.registrationStartsAt <= new Date()}
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
      <button
        class="top-margin-small secondary"
        onclick={() =>
          ui_object.changePath({ main: "main", sub: "invitation" })}
      >
        <i>person_add</i>
        <span>Gast einladen</span>
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
