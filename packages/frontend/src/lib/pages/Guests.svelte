<script lang="ts">
  import { ui_object, type RouteHost } from "$lib/lib/UI.svelte";

  import Guest from "$lib/components/buttons/Guest.svelte";
  import type { GuestExtern, GuestIntern } from "$lib/api/types";

  let searchInput = $state("");

  const present = ["present", "anwesend", "da"];
  const notPresent = ["away", "abwesend", "weg"];

  const checkGuest = (guest: GuestIntern | GuestExtern, filter: string) => {
    const lowercase = filter.toLowerCase();

    if (
      (guest.present && present.some((v) => v == lowercase)) ||
      (!guest.present && notPresent.some((v) => v == lowercase))
    )
      return true;

    if (
      guest.firstName.toLowerCase() == lowercase ||
      guest.lastName.toLowerCase() == lowercase
    )
      return true;

    if (
      !guest.extern &&
      (guest.residence == lowercase || guest.roomNumber.toString() == lowercase)
    )
      return true;

    return false;
  };

  const filterGuests = (
    search: String,
    guests: (GuestIntern | GuestExtern)[],
  ) => {
    if (search.length == 0) {
      return guests;
    } else {
      const splitted = search.split(" ");

      return guests.filter((g) =>
        splitted.every((filter) => checkGuest(g, filter)),
      );
    }
  };
</script>

{#if (ui_object.path as RouteHost).sub === undefined}
  <div id="center-container" class="middle-align center-align">
    <h4>Willkommen Wirt*innen!</h4>
    <p>
      Auf dieser Seite könnt ihr die QR-Codes der Gäste scannen oder diese
      manuell auf der Gästeliste eintragen.
    </p>

    <div>
      <button
        class="top-margin"
        onclick={() =>
          ui_object.openEditDialog({
            title: "QR-Code scannen",
            type: "qrcode",
          })}
      >
        <i>qr_code</i>
        <span>QR-Code scannen</span>
      </button>
      <button
        class="top-margin secondary"
        onclick={() => ((ui_object.path as RouteHost).sub = "list")}
      >
        <i>checklist</i>
        <span>Zur Gästeliste</span>
      </button>
    </div>
  </div>
{:else}
  <header>
    <div
      id="search"
      class="field large round fill {ui_object.layout == 'mobile'
        ? 'prefix'
        : ''}"
    >
      {#if ui_object.layout == "mobile"}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <a id="left-button" class="wave" onclick={() => ui("#dialog-menu")}>
          <i>menu</i>
        </a>
      {/if}

      <input placeholder="Search for guests" bind:value={searchInput} />

      <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
      <a id="right-button" class="wave" onclick={() => ui("#dialog-menu")}>
        <i>search</i>
      </a>
    </div>
  </header>

  <div id="guests">
    {#each filterGuests(searchInput, ui_object.guests) as guest, i}
      {#if i != 0}
        <hr />
      {/if}

      <Guest {guest} />
    {/each}
  </div>
{/if}

<style>
  #center-container {
    height: 100%;
    width: 100%;

    flex-flow: column;
  }

  .field {
    margin-block-start: 8px;
    margin-block-end: 8px;
  }

  #search.field > a#left-button {
    inset: 50% auto auto 0.4rem;
  }

  #search.field > a#right-button {
    inset: 50% 0.4rem auto auto;
  }

  #left-button,
  #right-button {
    block-size: 2.5rem;
    inline-size: 2.5rem;
  }

  #guests {
    height: calc(100vh - 72px);
    overflow-y: auto;
  }
</style>
