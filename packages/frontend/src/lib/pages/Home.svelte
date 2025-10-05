<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  let extended = $state(false);
  let hostCapability = $derived(
    ui_object.capabilities.some((c) => c == "host"),
  );
  let adminCapability = $derived(
    ui_object.capabilities.some((c) => c == "admin"),
  );
</script>

<div id="center-container" class="medium-padding middle-align center-align">
  <span class="expand"></span>

  {#if adminCapability}
    <h6 class="no-margin">Angemeldet mit dem Administrator-Konto</h6>
  {:else}
    <h6 class="no-margin">
      Willkommen auf der Stüble-Website! Habt ihr Lust mit uns zu feiern?
    </h6>
  {/if}

  {#if ui_object.status?.date !== undefined}
    <p>
      Das Motto am <span class="primary-text bold"
        >{ui_object.status.date.toLocaleDateString("de-DE")}
      </span> lautet:
    </p>
  {:else}
    <p>Das Motto lautet:</p>
  {/if}

  <h5 class="primary-text bold medium-margin">{settings.settings["motto"]}</h5>

  {#if !extended}
    <div id="partial-text" class="no-margin row wrap center-align">
      <p>{settings.settings["description"]?.split(" ", 7).join(" ")}</p>
      <button class="chip fill round" onclick={() => (extended = true)}>
        ...
      </button>
    </div>
  {:else if settings.settings["description"] !== undefined}
    <p class="no-margin">
      {#each settings.settings["description"]?.split("\n") as line}
        {line}<br />
      {/each}
    </p>
  {/if}

  {#if !hostCapability && !ui_object.status?.registered}
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
    {#if !hostCapability}
      <p class="bold">Du bist angemeldet!</p>
    {/if}

    <div>
      {#if !hostCapability}
        <button
          class="top-margin-small"
          onclick={() => ui_object.openDialog({ mode: "qrcode" })}
        >
          <i>qr_code</i>
          <span>QR-Code anzeigen</span>
        </button>
      {/if}
      {#if !adminCapability}
        <button
          class="top-margin-small secondary"
          onclick={() =>
            ui_object.changePath({ main: "start", sub: "einladen" })}
        >
          <i>person_add</i>
          <span>Externer Gast</span>
        </button>
      {/if}
    </div>

    <span class="expand"></span>

    {#if ui_object.status !== undefined && ui_object.status.registered && !ui_object.status.present}
      <p class="no-margin">Doch kein Bock?</p>

      <button
        class="large-margin"
        onclick={async () =>
          (await ui_object.openDialog({
            mode: "confirm",
            title: "Von Stüble abmelden",
            description: `Möchtest du dich wirklich vom Stüble abmelden? Eingeladene Gäste werden ebenfalls abgemeldet.${hostCapability ? " Beachte, dass Du hiermit deine Rechte als Wirt*in verlierst." : ""}`,
          })) && apiClient("http").removeFromGuestList()}
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

    padding-left: 16px;
    padding-right: 16px;

    flex-flow: column;
  }

  #partial-text {
    gap: 0.5rem;
  }

  .expand {
    flex-grow: 1;
  }
</style>
