<script lang="ts">
  import { page } from "$app/state";
  import { apiClient } from "$lib/api/client";
  import { onMount } from "svelte";

  let loading = $state(true);
  let result = $state<boolean>();

  onMount(async () => {
    const token = page.url.searchParams.get("token");

    if (token) {
      result = await apiClient("http").verifyAccount(token);

      loading = false;
      if (result) location.href = "/";
    }
  });
</script>

<article class="center middle absolute middle-align center-align border">
  <div>
    {#if !loading && !result}
      <h5>Fehler bei der Verifikation des Accounts</h5>

      <p>Versuche, dich erneut zu registrieren</p>

      <button class="margin" onclick={() => (location.href = "/setup")}>Zur Login-Seite</button
      >
    {:else if page.url.searchParams.get("token") == null}
      <h5>Fehler bei der Verifikation des Accounts</h5>

      <p>Fehlender Token</p>
    {/if}
  </div>
</article>
