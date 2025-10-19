<script lang="ts">
  import { apiClient, networkError } from "$lib/api/client";
  import { database } from "$lib/lib/database.svelte";
  import { ui_object, type DialogCheckIn } from "$lib/lib/UI.svelte";

  let guest = $derived((ui_object.dialogProperties as DialogCheckIn).guest);

  const checkIn = async () => {
    const data = { id: guest.id, present: true };

    try {
      await apiClient("http").modifyGuest(data);
      let g = database.guests.find((g) => g.id == guest.id);
      if (g === undefined) g = guest;

      const modifiedGuest = { ...g, verified: true };
      database.addGuests([modifiedGuest]);
    } catch (e) {
      if (networkError(e)) {
        database.addToBuffer({
          action: "modifyGuest",
          data,
        });
      }
    }
  };

  const verify = async () => {
    if (!guest.extern) {
      const data = { id: guest.id, verified: true };

      try {
        await apiClient("http").modifyUser(data);

        let g = database.guests.find((g) => g.id == guest.id);
        if (g === undefined) g = guest;

        const modifiedGuest = { ...g, verified: true };
        database.addGuests([modifiedGuest]);
      } catch (e) {
        if (networkError(e)) {
          database.addToBuffer({
            action: "modifyUser",
            data,
          });
        }
      }
    }
  };
</script>

<div class="row">
  <p class="max" style="font-size: large;">
    {guest.firstName ?? ""}
    {guest.lastName ?? ""}
  </p>

  {#if !guest.extern}
    <button
      class="chip round not-clickable {guest.verified
        ? 'green black-text'
        : 'error-container'}"
    >
      {!guest.verified ? "Überprüfen" : "Bestätigt"}
    </button>
  {/if}
</div>

{#if !guest.extern && !guest.verified}
  <ul>
    <li>Möchtest du diese Person einlassen?</li>
    <li>Kannst du den Namen dieser Person bestätigen?</li>
  </ul>

  <nav id="buttons" class="right-align">
    <button
      class="transparent error-text"
      onclick={() => ui_object.closeDialog(false)}>Abbruch</button
    >
    <button
      class="transparent link"
      onclick={async () => {
        await checkIn();
        ui_object.closeDialog(true);
      }}>Temporär</button
    >
    <button
      onclick={async () => {
        await verify();
        await checkIn();
        ui_object.closeDialog(true);
      }}>Bestätigen</button
    >
  </nav>
{:else}
  <p>Möchtest du diese Person einlassen?</p>

  <nav id="buttons" class="right-align">
    <button
      class="transparent error-text"
      onclick={() => ui_object.closeDialog(false)}>Abbruch</button
    >
    <button
      onclick={async () => {
        await checkIn();
        ui_object.closeDialog(true);
      }}>Einlassen</button
    >
  </nav>
{/if}

<style>
  .not-clickable {
    pointer-events: none;
  }

  #buttons {
    gap: 8px;
  }
</style>
