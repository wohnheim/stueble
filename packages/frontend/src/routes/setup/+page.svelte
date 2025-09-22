<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";

  import { apiClient } from "$lib/api/client";
  import { database } from "$lib/lib/database.svelte";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object, WohnheimType } from "$lib/lib/UI.svelte";

  import logo from "$lib/assets/Fileplay.svg";

  /* Navigation */

  let progress = $state(0);
  let progress2Mode = $state<"login" | "register">("login");

  /* Input state */

  let firstNameValid = $state(true);
  let lastNameValid = $state(true);
  let roomNumberValid = $state(true);
  let passwordValid = $state(true);
  let usernameValid = $state(true);

  let emailValid = $state(true);
  let emailInput = $state<HTMLInputElement>();

  let privacyPolicy = $state(false);

  /* Input validation */

  let registerButtonDisabled = $derived(
    ui_object.userParams.firstName == "" ||
      ui_object.userParams.lastName == "" ||
      ui_object.userParams.email == "" ||
      !emailInput?.validity.valid ||
      ui_object.userParams.roomNumber == 0 ||
      ui_object.userParams.roomNumber % 1 != 0 ||
      ui_object.userParams.password == "" ||
      ui_object.userParams.username == "" ||
      ui_object.userParams.username.includes("@") ||
      !privacyPolicy,
  );
  let loginButtonDisabled = $derived(
    ui_object.userParams.username == "" || ui_object.userParams.password == "",
  );

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && progress == 2) {
      if (progress2Mode == "register" && !registerButtonDisabled) {
        register();
      } else if (progress2Mode == "login" && !loginButtonDisabled) {
        login();
      }
    }
  };

  const login = async () => {
    const res = await apiClient("http").login(
      ui_object.userParams.username,
      ui_object.userParams.password,
    );

    if (res) {
      localStorage.setItem("loggedIn", "true");

      await settings.init();
      await settings.clear();
      await database.init();
      await database.clear();
      location.href = "/";
    }
  };

  const register = async () => {
    const res = await apiClient("http").createAccount(
      {
        firstName: ui_object.userParams.firstName,
        lastName: ui_object.userParams.lastName,
        roomNumber: ui_object.userParams.roomNumber,
        residence: ui_object.userParams.residence,
      },
      ui_object.userParams.email,
      ui_object.userParams.password,
      ui_object.userParams.username,
    );

    if (res) {
      localStorage.setItem("loggedIn", "true");

      await settings.init();
      await settings.clear();
      await database.init();
      await database.clear();
      location.href = "/";
    }
  };

  onMount(() => {
    progress = 1;
  });
</script>

<svelte:window on:dragover|preventDefault on:keydown={handleKeyDown} />

{#if progress == 1}
  <div id="logo" in:fade={{ duration: 200 }}>
    <img id="logo-image" src={logo} alt="Stüble" draggable="false" />
  </div>

  <div id="start" class="center-align middle-align" in:fade={{ duration: 200 }}>
    <nav class="group split">
      <button
        class="left-round large"
        onclick={() => {
          progress = 2;
          progress2Mode = "login";
        }}
      >
        <span>Anmelden</span>
      </button>
      <button
        class="right-round secondary large"
        onclick={() => {
          progress = 2;
          progress2Mode = "register";
        }}
      >
        <span>Registrieren</span>
      </button>
    </nav>
  </div>
{:else if progress == 2}
  <article class="center absolute middle-align center-align border">
    <div>
      {#if progress2Mode == "login"}
        <h5>Anmelden</h5>
        <div class="space"></div>
        <div
          class="max field border round label {usernameValid
            ? ''
            : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.username}
            onchange={() => (usernameValid = !!ui_object.userParams.username)}
            onfocusout={() => (usernameValid = !!ui_object.userParams.username)}
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>E-Mail oder Benutzername</label>
          {#if !usernameValid}
            <i>error</i>
            <span class="error">Ein Benutzername wird benötigt</span>
          {/if}
        </div>

        <div
          class="max field border round label {passwordValid
            ? ''
            : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.password}
            onchange={() => (passwordValid = !!ui_object.userParams.password)}
            onfocusout={() => (passwordValid = !!ui_object.userParams.password)}
            type="password"
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Passwort</label>
          {#if !passwordValid}
            <i>error</i>
            <span class="error">Ein Passwort wird benötigt</span>
          {/if}
        </div>

        <button class="large" disabled={loginButtonDisabled} onclick={login}
          >Anmelden</button
        >
      {:else}
        <h5>Registrieren</h5>
        <div class="space"></div>

        <div
          class="field border label {firstNameValid ? '' : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.firstName}
            oninput={() => (firstNameValid = !!ui_object.userParams.firstName)}
            onfocusout={() =>
              (firstNameValid = !!ui_object.userParams.firstName)}
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Vorname</label>
          {#if !firstNameValid}
            <i>error</i>
            <span class="error">Diese Angabe ist erforderlich</span>
          {/if}
        </div>

        <div class="field border label {lastNameValid ? '' : 'invalid suffix'}">
          <input
            bind:value={ui_object.userParams.lastName}
            oninput={() => (lastNameValid = !!ui_object.userParams.lastName)}
            onfocusout={() => (lastNameValid = !!ui_object.userParams.lastName)}
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Nachname</label>
          {#if !lastNameValid}
            <i>error</i>
            <span class="error">Diese Angabe ist erforderlich</span>
          {/if}
        </div>

        <div
          class="field border label {roomNumberValid ? '' : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.roomNumber}
            oninput={() =>
              (roomNumberValid =
                !!ui_object.userParams.roomNumber &&
                ui_object.userParams.roomNumber % 1 == 0 &&
                ui_object.userParams.roomNumber != 0)}
            onfocusout={() =>
              (roomNumberValid =
                !!ui_object.userParams.roomNumber &&
                ui_object.userParams.roomNumber % 1 == 0 &&
                ui_object.userParams.roomNumber != 0)}
            type="number"
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Zimmernummer</label>
          {#if !roomNumberValid}
            <i>error</i>
            <span class="error">Fehlerhafte Eingabe</span>
          {/if}
        </div>

        <div class="field border label">
          <select
            bind:value={ui_object.userParams.residence}
            style="min-width: 200px;"
          >
            {#each Object.entries(WohnheimType) as [label, value]}
              <option {value}>{label}</option>
            {/each}
          </select>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Wohnheim</label>
        </div>

        <p>Anmeldedaten</p>

        <div
          class="max field border round label {usernameValid
            ? ''
            : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.username}
            onchange={() => (usernameValid = !!ui_object.userParams.username)}
            onfocusout={() => (usernameValid = !!ui_object.userParams.username)}
            type="email"
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Benutzername</label>
          {#if !usernameValid}
            <i>error</i>
            <span class="error">Ein Benutzername wird benötigt</span>
          {/if}
        </div>

        <div
          class="max field border round label {emailValid
            ? ''
            : 'invalid suffix'}"
        >
          <input
            bind:this={emailInput}
            bind:value={ui_object.userParams.email}
            onchange={() =>
              (emailValid =
                (emailInput?.validity.valid ?? false) &&
                !!ui_object.userParams.email)}
            onfocusout={() =>
              (emailValid =
                (emailInput?.validity.valid ?? false) &&
                !!ui_object.userParams.email)}
            type="email"
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>E-Mail-Adresse</label>
          {#if !emailValid}
            <i>error</i>
            {#if !ui_object.userParams.email}
              <span class="error">Eine E-Mail-Adresse wird benötigt</span>
            {:else}
              <span class="error">Geben Sie eine valide E-Mail-Adresse ein</span
              >
            {/if}
          {/if}
        </div>

        <div
          class="max field border round label {passwordValid
            ? ''
            : 'invalid suffix'}"
        >
          <input
            bind:value={ui_object.userParams.password}
            onchange={() => (passwordValid = !!ui_object.userParams.password)}
            onfocusout={() => (passwordValid = !!ui_object.userParams.password)}
            type="password"
          />
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label>Passwort</label>
          {#if !passwordValid}
            <i>error</i>
            <span class="error">Ein Passwort wird benötigt</span>
          {/if}
        </div>

        <label class="checkbox">
          <input bind:checked={privacyPolicy} type="checkbox" />
          <span
            >Ich stimme der Nutzung meiner Daten zur Verifikation der
            Korrektheit und Nutzung der Anwendung zu.</span
          >
        </label>

        <button
          class="large"
          disabled={registerButtonDisabled}
          onclick={register}>Registrieren</button
        >
      {/if}
    </div>
  </article>
{/if}

<style>
  #logo {
    position: absolute;
    width: 100%;
    height: 50%;
    top: 0;

    display: flex;
    justify-content: center;
    align-items: center;
  }

  #start {
    position: absolute;
    width: 100%;
    height: 50%;
    bottom: 0;
  }

  img#logo-image {
    width: 300px;
    height: auto;
  }
</style>
