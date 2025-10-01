<script lang="ts">
  import { onMount } from "svelte";

  import type { Host } from "$lib/api/types";
  import { database } from "$lib/lib/database.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Hosts from "$lib/pages/Hosts.svelte";

  let hostsPage = $state<"list" | "add">("list");
  let hostsSelectedUnfiltered = $state<Host[]>([]);
  let hostsSelected = $derived(
    hostsSelectedUnfiltered.filter(
      (u) => !database.hosts.some((h) => u.id == h.id),
    ),
  );
  let hostsSearchInput = $state("");
  let hostsSearchResultsUnfiltered = $state<Host[]>([]);
  let hostsSearchResults = $derived(
    hostsSearchResultsUnfiltered.filter(
      (u) => !database.hosts.some((h) => u.id == h.id),
    ),
  );

  onMount(() => {
    ui_object.largeDialog?.addEventListener("close", () => {
      if (ui_object.path.main == "einstellungen" && ui_object.path.sub !== undefined)
        ui_object.changePath({ main: "einstellungen" });

      if (hostsPage)
        setTimeout(() => {
          hostsPage = "list";
          hostsSelectedUnfiltered = [];
          hostsSearchInput = "";
          hostsSearchResultsUnfiltered = [];
        }, 400);
    });
  });
</script>

<dialog id="dialog-large" bind:this={ui_object.largeDialog} class="right large">
  {#if ui_object.path.main == "einstellungen"}
    <Hosts
      title={ui_object.path.sub == "wirte" ? "Wirt*innen": "Tutor*innen"}
      bind:page={hostsPage}
      bind:selectedUnfiltered={hostsSelectedUnfiltered}
      bind:selected={hostsSelected}
      bind:searchInput={hostsSearchInput}
      bind:searchResultsUnfiltered={hostsSearchResultsUnfiltered}
      bind:searchResults={hostsSearchResults}
    />
  {/if}
</dialog>

<style>
  #dialog-large {
    padding: 0;
  }
</style>
