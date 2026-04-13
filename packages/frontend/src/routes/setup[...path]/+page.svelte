<script lang="ts">
  import { browser } from "$app/environment";
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import z from "zod";

  import { apiClient } from "$lib/api/client";
  import { database } from "$lib/lib/database.svelte";
  import { Routing } from "$lib/lib/routing.svelte";
  import { settings } from "$lib/lib/settings.svelte";
  import { ui_object, WohnheimType } from "$lib/lib/UI.svelte";

  import Logo from "$lib/assets/Stueble.svelte";
  import Snackbar from "$lib/components/Snackbar.svelte";

  /* Navigation */

  let loaded = $state(false);

  const routeSetup = z.object({
    main: z.enum(["setup"]),
    sub: z.enum(["login", "register", "email", "password-reset"]).optional(),
  });

  const routing = new Routing(routeSetup, { main: "setup" });
  let resetStage = $state<"request-token" | "reset-password">("request-token");

  /* Input state */

  let token = $state("");

  let firstNameValid = $state(true);
  let lastNameValid = $state(true);
  let residenceValid = $state(true);
  let roomNumberValid = $state(true);
  let passwordValid = $state(true);
  let usernameValid = $state(true);
  let tokenValid = $state(true);

  let emailValid = $state(true);
  let emailInput = $state<HTMLInputElement>();

  let privacyPolicy = $state(false);
  let tokenInputDisabled = $state(false);

  /* Input validation */

  let registerButtonDisabled = $derived(
    token == "" ||
      ui_object.userParams.firstName == "" ||
      ui_object.userParams.lastName == "" ||
      ui_object.userParams.email == "" ||
      !emailInput?.validity.valid ||
      ui_object.userParams.residence == "" ||
      ui_object.userParams.roomNumber == "" ||
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
  let resetButtonDisabled = $derived(
    (resetStage == "request-token" && ui_object.userParams.username == "") ||
      (resetStage == "reset-password" &&
        (token == "" || ui_object.userParams.password == "")),
  );

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") {
      if (routing.path.sub == "register" && !registerButtonDisabled) {
        register();
      } else if (routing.path.sub == "login" && !loginButtonDisabled) {
        login();
      } else if (routing.path.sub == "password-reset" && !resetButtonDisabled) {
        if (resetStage == "request-token") {
          passwordReset();
        } else {
          confirmPasswordReset();
        }
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
    if (
      ui_object.userParams.roomNumber == "" ||
      ui_object.userParams.residence == ""
    )
      return;

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
      token,
    );

    if (res) routing.changePath({ main: "setup", sub: "email" });
  };

  const passwordReset = async () => {
    const res = await apiClient("http").resetPassword(
      ui_object.userParams.username,
    );

    if (res) {
      resetStage = "reset-password";
    }
  };

  const confirmPasswordReset = async () => {
    const res = await apiClient("http").confirmPasswordReset(
      token,
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

  onMount(() => {
    if (!loaded) {
      loaded = true;

      const tmpToken = page.url.searchParams.get("token");
      if (tmpToken !== null) {
        token = tmpToken;

        resetStage = "reset-password";
        tokenInputDisabled = true;
      }
    }
  });

  $effect(() => {
    if (browser)
      routing.path = routing.getPath(location.pathname, page.url.pathname);
  });
</script>

<svelte:window
  bind:innerHeight={ui_object.height}
  bind:innerWidth={ui_object.width}
  on:dragover|preventDefault
  on:keydown={handleKeyDown}
/>

<Snackbar />

{#if loaded == true}
  {#if routing.path.sub === undefined}
    <div id="logo" in:fade={{ duration: 200 }}>
      <Logo />
    </div>

    <div
      id="start"
      class="center-align middle-align"
      in:fade={{ duration: 200 }}
    >
      <nav class="group split">
        <button
          class="left-round large"
          onclick={() => routing.changePath({ main: "setup", sub: "login" })}
        >
          <span>Anmelden</span>
        </button>
        <button
          class="right-round secondary large"
          onclick={() => routing.changePath({ main: "setup", sub: "register" })}
        >
          <span>Registrieren</span>
        </button>
      </nav>
    </div>
  {:else if routing.path.sub == "email"}
    <div id="center-container" class="medium-padding middle-align center-align">
      <h6>Account erfolgreich erstellt</h6>

      <p>Ein Aktivierungslink wurde an deine E-Mail-Adresse gesendet.</p>
    </div>
  {:else}
    {#snippet progress2Snippet(classes: string)}
      <div class={classes}>
        {#if routing.path.sub == "login"}
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
              onfocusout={() =>
                (usernameValid = !!ui_object.userParams.username)}
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
              onfocusout={() =>
                (passwordValid = !!ui_object.userParams.password)}
              type="password"
            />
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label>Passwort</label>
            {#if !passwordValid}
              <i>error</i>
              <span class="error">Ein Passwort wird benötigt</span>
            {/if}
          </div>

          <button
            class="large top-margin"
            disabled={loginButtonDisabled}
            onclick={login}>Anmelden</button
          >

          <div class="max top-margin secondary-text">
            <!-- svelte-ignore a11y_missing_attribute, a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
            <a
              onclick={() =>
                routing.changePath({ main: "setup", sub: "password-reset" })}
              >Passwort vergessen?</a
            >
          </div>
        {:else if routing.path.sub == "password-reset"}
          <h5>Passwort zurücksetzen</h5>
          <div class="space"></div>

          {#if resetStage == "request-token" || ui_object.userParams.username != ""}
            <div
              class="max field border round label {usernameValid
                ? ''
                : 'invalid suffix'}"
            >
              <input
                bind:value={ui_object.userParams.username}
                disabled={resetStage == "reset-password"}
                onchange={() =>
                  (usernameValid = !!ui_object.userParams.username)}
                onfocusout={() =>
                  (usernameValid = !!ui_object.userParams.username)}
              />
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label>E-Mail oder Benutzername</label>
              {#if !usernameValid}
                <i>error</i>
                <span class="error">Ein Benutzername wird benötigt</span>
              {/if}
            </div>
          {/if}

          {#if resetStage == "reset-password"}
            <div
              class="max field border round label {tokenValid
                ? ''
                : 'invalid suffix'}"
            >
              <input
                bind:value={token}
                disabled={tokenInputDisabled}
                onchange={() => (tokenValid = !!token)}
                onfocusout={() => (tokenValid = !!token)}
              />
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label>Token aus E-Mail</label>
              {#if !tokenValid}
                <i>error</i>
                <span class="error">Ein Token wird benötigt</span>
              {/if}
            </div>

            <div
              class="max field border round label {passwordValid
                ? ''
                : 'invalid suffix'}"
            >
              <input
                bind:value={ui_object.userParams.password}
                onchange={() =>
                  (passwordValid = !!ui_object.userParams.password)}
                onfocusout={() =>
                  (passwordValid = !!ui_object.userParams.password)}
                type="password"
              />
              <!-- svelte-ignore a11y_label_has_associated_control -->
              <label>Passwort</label>
              {#if !passwordValid}
                <i>error</i>
                <span class="error">Ein Passwort wird benötigt</span>
              {/if}
            </div>
          {/if}

          <button
            class="large top-margin"
            disabled={resetButtonDisabled}
            onclick={resetStage == "request-token"
              ? passwordReset
              : confirmPasswordReset}
            >{resetStage == "request-token"
              ? "E-Mail anfordern"
              : "Zurücksetzen"}</button
          >
        {:else}
          <h5>Registrieren</h5>
          <div class="space"></div>

          <div
            class="max field border round label {tokenValid
              ? ''
              : 'invalid suffix'}"
          >
            <input
              bind:value={token}
              disabled={tokenInputDisabled}
              onchange={() => (tokenValid = !!token)}
              onfocusout={() => (tokenValid = !!token)}
            />
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label>Registrierungstoken von den Tutoren</label>
            {#if !tokenValid}
              <i>error</i>
              <span class="error"
                >Ein Token wird benötigt um Spam zu verhindern. Wende dich an
                die Tutoren für einen neuen Token.</span
              >
            {/if}
          </div>

          <p>Persönliche Daten</p>

          <div
            class="field border label {firstNameValid ? '' : 'invalid suffix'}"
          >
            <input
              bind:value={ui_object.userParams.firstName}
              oninput={() =>
                (firstNameValid = !!ui_object.userParams.firstName)}
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

          <div
            class="field border label {lastNameValid ? '' : 'invalid suffix'}"
          >
            <input
              bind:value={ui_object.userParams.lastName}
              oninput={() => (lastNameValid = !!ui_object.userParams.lastName)}
              onfocusout={() =>
                (lastNameValid = !!ui_object.userParams.lastName)}
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

          <div
            class="field border label {residenceValid ? '' : 'invalid suffix'}"
          >
            <select
              bind:value={ui_object.userParams.residence}
              style="min-width: 200px;"
              onfocusout={() =>
                (residenceValid = !!ui_object.userParams.residence)}
            >
              <option value={""}></option>
              {#each Object.entries(WohnheimType) as [label, value]}
                <option {value}>{label}</option>
              {/each}
            </select>
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label>Wohnheim</label>
            {#if !residenceValid}
              <i>error</i>
              <span class="error">Diese Angabe ist erforderlich</span>
            {/if}
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
              onfocusout={() =>
                (usernameValid = !!ui_object.userParams.username)}
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
                <span class="error"
                  >Geben Sie eine valide E-Mail-Adresse ein</span
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
              onfocusout={() =>
                (passwordValid = !!ui_object.userParams.password)}
              type="password"
            />
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label>Passwort</label>
            {#if !passwordValid}
              <i>error</i>
              <span class="error">Ein Passwort wird benötigt</span>
            {/if}
          </div>

          <label class="checkbox left-margin bottom-margin top-margin">
            <input bind:checked={privacyPolicy} type="checkbox" />
            <span class="wrap"
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
    {/snippet}

    {#if ui_object.layout == "desktop"}
      <article
        id="main-article"
        class="center absolute middle-align center-align border"
      >
        {@render progress2Snippet("")}
      </article>
    {:else}
      {@render progress2Snippet("large-padding center-align")}
    {/if}
  {/if}
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

  #main-article {
    width: 600px;
    min-width: 290px;
  }

  #center-container {
    height: 100%;
    width: 100%;

    padding-left: 16px;
    padding-right: 16px;

    flex-flow: column;
  }
</style>
