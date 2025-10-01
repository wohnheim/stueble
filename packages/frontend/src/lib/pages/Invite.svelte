<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { ui_object } from "$lib/lib/UI.svelte";

  let vornameValid = $state(true);
  let nachnameValid = $state(true);

  let emailValid = $state(true);
  let emailInput = $state<HTMLInputElement>();
</script>

<div class="margin">
  <h6 class="centered-text">Gast einladen</h6>

  <p>
    Auf dieser Seite kannst du einen Gast zum nächsten Stüble einladen. Gib dazu
    den Namen und eine E-Mail-Adresse an, an die der QR-Code des Gasts geschickt
    werden soll.
  </p>

  <div class="field border label {vornameValid ? '' : 'invalid suffix'}">
    <input
      bind:value={ui_object.userParams.firstName}
      oninput={() => (vornameValid = !!ui_object.userParams.firstName)}
      onfocusout={() => (vornameValid = !!ui_object.userParams.firstName)}
    />
    <!-- svelte-ignore a11y_label_has_associated_control -->
    <label>Vorname</label>
    {#if !vornameValid}
      <i>error</i>
      <span class="error">Diese Angabe ist erforderlich</span>
    {/if}
  </div>

  <div class="field border label {nachnameValid ? '' : 'invalid suffix'}">
    <input
      bind:value={ui_object.userParams.lastName}
      oninput={() => (nachnameValid = !!ui_object.userParams.lastName)}
      onfocusout={() => (nachnameValid = !!ui_object.userParams.lastName)}
    />
    <!-- svelte-ignore a11y_label_has_associated_control -->
    <label>Nachname</label>
    {#if !nachnameValid}
      <i>error</i>
      <span class="error">Diese Angabe ist erforderlich</span>
    {/if}
  </div>

  <div class="field border label {emailValid ? '' : 'invalid suffix'}">
    <input
      bind:this={emailInput}
      bind:value={ui_object.userParams.email}
      onchange={() =>
        (emailValid =
          ui_object.userParams.email.length == 0 ||
          (emailInput?.validity.valid ?? false))}
      onfocusout={() =>
        (emailValid =
          ui_object.userParams.email.length == 0 ||
          (emailInput?.validity.valid ?? false))}
      type="email"
    />
    <!-- svelte-ignore a11y_label_has_associated_control -->
    <label>E-Mail-Adresse</label>
    {#if !emailValid}
      <i>error</i>
      <span class="error">Gib eine valide E-Mail-Adresse ein</span>
    {/if}
  </div>

  <button
    class="center"
    disabled={ui_object.userParams.firstName == "" ||
      ui_object.userParams.lastName == "" ||
      (ui_object.userParams.email != "" && !emailInput.validity.valid)}
    onclick={() =>
      apiClient("http").inviteExtern(
        ui_object.userParams.firstName,
        ui_object.userParams.lastName,
        ui_object.userParams.email != ""
          ? ui_object.userParams.email
          : undefined,
      )}
  >
    <i>send</i>
    <span>Einladen</span>
  </button>
</div>

<style>
  .centered-text {
    text-align: center;
  }
</style>
