<script lang="ts">
  import { page } from "$app/state";
  import { onMount } from "svelte";

  import { apiClient } from "$lib/api/client";
  import { settings } from "$lib/lib/settings.svelte";
  import { database } from "$lib/lib/database.svelte";

  import Snackbar from "$lib/components/Snackbar.svelte";

  let loading = $state(true);
  let result = $state<boolean>();

  onMount(async () => {
    const token = page.url.searchParams.get("token");

    if (token) {
      result = await apiClient("http").verifyAccount(token);

      loading = false;
      if (result) {
        localStorage.setItem("loggedIn", "true");

        await settings.init();
        await settings.clear();
        await database.init();
        await database.clear();
        location.href = "/";
      }
    }
  });
</script>

<Snackbar />

<article class="center middle absolute middle-align center-align border">
  <div>
    {#if !loading && !result}
      <h5>Fehler bei der Verifikation des Accounts</h5>

      <p>Versuche, dich erneut zu registrieren</p>

      <button class="margin" onclick={() => (location.href = "/setup")}>
        Zur Login-Seite
      </button>
    {:else if page.url.searchParams.get("token") == null}
      <h5>Fehler bei der Verifikation des Accounts</h5>

      <p>Fehlender Token</p>
    {/if}
  </div>
</article>
