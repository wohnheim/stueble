<script lang="ts">
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { error } from "$lib/lib/error";
  import { ui_object, type RouteApplication } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";

  let showPriorities = $state(false);

  let motto = $state("");
  let mottoValid = $state(true);

  let dates = $state<Date[]>([]);
  let selectedDates = $state<[Date, number][]>([]);

  let dateInputCheckedValues = $state<boolean[]>([]);
  let dateInputNumberValues = $state<(number | undefined)[]>([]);

  const onDateInput = (
    index: number,
    event: Event & {
      currentTarget: EventTarget & HTMLInputElement;
    },
  ) => {
    if (showPriorities) {
      const value = event.currentTarget.valueAsNumber;
      const selected_index = selectedDates.findIndex(
        (d) => d[0].getTime() === dates[index]?.getTime(),
      );

      if (!value || Number.isNaN(value)) {
        if (selected_index != -1) selectedDates.splice(selected_index, 1);
        dateInputCheckedValues[index] = false;
      } else {
        if (selected_index != -1) selectedDates[selected_index]![1] = value;
        else selectedDates.push([dates[index]!, value]);
        dateInputCheckedValues[index] = true;
      }
    } else {
      const value = event.currentTarget.checked;
      const selected_index = selectedDates.findIndex(
        (d) => d[0].getTime() === dates[index]?.getTime(),
      );

      if (!value) {
        if (selected_index != -1) selectedDates.splice(selected_index, 1);
        dateInputNumberValues[index] = undefined;
      } else {
        if (selected_index != -1) selectedDates[selected_index]![1] = 1;
        else selectedDates.push([dates[index]!, 1]);
        dateInputNumberValues[index] = 1;
      }
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
    dateInputCheckedValues.length = dates.length;
    dateInputNumberValues.length = dates.length;

    dates = await apiClient("http").getDates();
  });
</script>

<div class="margin">
  <h6 class="centered-text">Termin-Anmeldung</h6>

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
    <nav class="wrap">
      {#if showPriorities}
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
      {:else}
        {#each dates as date, index}
          <label class="checkbox">
            <input
              type="checkbox"
              bind:checked={dateInputCheckedValues[index]}
              oninput={(e) => onDateInput(index, e)}
            />
            <span>{date.toLocaleDateString("de-DE")}</span>
          </label>
        {/each}
      {/if}
    </nav>

    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_missing_attribute -->
    <a
      id="priorities"
      class="primary-text"
      onclick={() => (showPriorities = !showPriorities)}
      >Prioritäten {showPriorities ? "ausblenden" : "einblenden"}</a
    >
  </fieldset>

  <fieldset>
    <legend>Wirt*innen</legend>
    <ul>
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
    disabled={motto == "" || ui_object.applicationHosts.length == 0}
    onclick={() =>
      apiClient("http")
        .submitApplication(
          motto,
          ui_object.applicationHosts.map((h) => h.id),
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

  #priorities {
    margin-top: 14px;
  }

  #send-button {
    margin-top: 32px;
  }

  .centered-text {
    text-align: center;
  }
</style>
