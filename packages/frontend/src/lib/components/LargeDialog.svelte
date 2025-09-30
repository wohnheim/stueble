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

  onMount(() => {
    ui_object.largeDialog?.addEventListener("close", () => {
      if (ui_object.path.main == "settings" && ui_object.path.sub !== undefined)
        ui_object.changePath({ main: "settings" });

      if (hostsPage)
        setTimeout(() => {
          hostsPage = "list";
          hostsSelectedUnfiltered = [];
        }, 400);
    });
  });
</script>

<dialog id="dialog-large" bind:this={ui_object.largeDialog} class="right large">
  {#if ui_object.path.main == "settings"}
    <Hosts
      bind:page={hostsPage}
      bind:selectedUnfiltered={hostsSelectedUnfiltered}
      bind:selected={hostsSelected}
    />
  {/if}
</dialog>

<style>
  #dialog-large {
    padding: 0;
  }
</style>
