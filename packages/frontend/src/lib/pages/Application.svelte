<script lang="ts">
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { error } from "$lib/lib/error";
  import { ui_object, type RouteApplication } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";

  let motto = $state("");
  let mottoValid = $state(true);

  let dates = $state<Date[]>([]);
  let selectedDates = $state<[Date, number][]>([]);

  let dateInputNumberValues = $state<(number | undefined)[]>([]);

  const onDateInput = (
    index: number,
    event: Event & {
      currentTarget: EventTarget & HTMLInputElement;
    },
  ) => {
    const value = event.currentTarget.valueAsNumber;
    const selected_index = selectedDates.findIndex(
      (d) => d[0].getTime() === dates[index]?.getTime(),
    );

    if (!value || Number.isNaN(value)) {
      if (selected_index != -1) selectedDates.splice(selected_index, 1);
    } else {
      if (selected_index != -1) selectedDates[selected_index]![1] = value;
      else selectedDates.push([dates[index]!, value]);
    }
  };

  // TBC: Generic dialog opening
  $effect(() => {
    // Open dialog
    if (
      (ui_object.routing.path as RouteApplication).sub &&
      ui_object.largeDialog &&
      !ui_object.largeDialog.open
    )
      ui(ui_object.largeDialog);

    // Close dialog
    if (
      (ui_object.routing.path as RouteApplication).sub === undefined &&
      ui_object.largeDialog &&
      ui_object.largeDialog.open
    )
      ui(ui_object.largeDialog);
  });

  onMount(async () => {
    dateInputNumberValues.length = dates.length;

    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDay())

    dates = (await apiClient("http").getDates()).filter(d => d >= today);
  });
</script>

<div id="scrollable" class="margin">
  <div class="row wrap center-align">
    <h6>Termin-Anmeldung</h6>

    <button class="chip round not-clickable orange7 black-text" tabindex="-1">
      Nachmeldephase
    </button>
  </div>

  <p>
    Auf dieser Seite kannst du deine WG für einen Stüble-Termin anmelden. Gib
    dazu das Motto, die für euch passenden Termine und die ausschenkenden
    WG-Mitglieder an.<br />
    Weitere Personen kannst du nach der Bestätigung des Termin jederzeit nachtragen.
  </p>

  <div class="field border label {mottoValid ? '' : 'invalid suffix'}">
    <input
      bind:value={motto}
      oninput={() => (mottoValid = !!motto)}
      onfocusout={() => (mottoValid = !!motto)}
    />
    <!-- svelte-ignore a11y_label_has_associated_control -->
    <label>Motto</label>
    {#if !mottoValid}
      <i>error</i>
      <span class="error">Diese Angabe ist erforderlich</span>
    {/if}
  </div>

  <fieldset>
    <legend>Freie Stüble-Termine</legend>
    <p>
      Hier kannst du deine präferierten Stüble-Termine auswählen. Der Termin mit
      Priorität 1 ist dein Lieblingstermin, die anderen Termine folgen
      aufsteigend. <br />
      Außerdem muss jedem Termin eine andere Priorität zugewiesen werden. Falls dir
      ein Termin nicht passt, kannst du das Feld einfach leer lassen.
    </p>

    <nav class="wrap">
      {#each dates as date, index}
        <label class="number row">
          <div class="field tiny border">
            <input
              type="number"
              min="1"
              max={dates.length}
              bind:value={dateInputNumberValues[index]}
              oninput={(e) => onDateInput(index, e)}
            />
          </div>
          <span>{date.toLocaleDateString("de-DE")}</span>
        </label>
      {/each}
    </nav>
  </fieldset>

  <fieldset>
    <legend>Wirt*innen</legend>
    <p>
      Mit dem unten stehenden Link kannst du die ausschenkenden WG-Mitglieder
      angeben. Achtung, du musst mindestens eine Person angeben.
    </p>

    <ul>
      <li>
        {ui_object.user?.firstName}
        {ui_object.user?.lastName} ({ui_object.user
          ? capitalizeFirstLetter(ui_object.user.residence)
          : ""})
      </li>

      {#each ui_object.applicationHosts as host}
        <li>
          {host.firstName}
          {host.lastName} ({capitalizeFirstLetter(host.residence)})
        </li>
      {/each}
    </ul>

    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_missing_attribute -->
    <a
      class="primary-text"
      onclick={() => {
        ui_object.routing.changePath({ main: "anmeldung", sub: "wirte" });
      }}>Hinzufügen / Entfernen</a
    >
  </fieldset>

  <button
    id="send-button"
    class="center"
    disabled={motto == "" ||
      selectedDates.length == 0 ||
      ui_object.applicationHosts.length == 0}
    onclick={() =>
      ui_object.user !== undefined &&
      apiClient("http")
        .submitApplication(
          motto,
          ui_object.applicationHosts
            .filter(
              (h) => ui_object.user !== undefined && h.id != ui_object.user.id,
            )
            .map((h) => h.id)
            .concat([ui_object.user.id]),
          selectedDates.filter((d) => d[1] >= 1),
        )
        .then(
          (res) =>
            res &&
            error.snackbar(
              "Deine Anmeldung wurde erfolgreich übertragen.",
              false,
              "check",
            ),
        )}
  >
    <i>send</i>
    <span>Absenden</span>
  </button>
</div>

<style>
  #scrollable {
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .not-clickable {
    pointer-events: none;
  }

  .field.tiny {
    --_input: 1.8rem;
  }

  label.number {
    gap: 0.5rem;
  }

  label.number > span {
    color: var(--on-surface);
    font-size: 0.875rem;
  }

  label.number input {
    text-align: center;
    width: 2.5rem;
    padding: 0;
  }

  #send-button {
    margin-top: 32px;
  }
</style>
