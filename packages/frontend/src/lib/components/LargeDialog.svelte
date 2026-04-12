<script lang="ts">
  import { onMount } from "svelte";

  import type { HostOrTutor } from "$lib/api/types";
  import { database } from "$lib/lib/database.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Hosts from "$lib/pages/Hosts.svelte";
  import { apiClient } from "$lib/api/client";

  let hostsPage = $state<"list" | "add">("list");
  let hostsSelectedUnfiltered = $state<HostOrTutor[]>([]);
  let hostsSearchInput = $state("");
  let hostsSearchResultsUnfiltered = $state<HostOrTutor[]>([]);

  onMount(() => {
    ui_object.largeDialog?.addEventListener("close", () => {
      if (
        (ui_object.routing.path.main == "einstellungen" ||
          ui_object.routing.path.main == "anmeldung") &&
        ui_object.routing.path.sub !== undefined
      )
        ui_object.routing.changePath({ main: ui_object.routing.path.main });

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
  {#if ui_object.routing.path.main == "einstellungen"}
    {#if ui_object.routing.path.sub == "wirte"}
      <Hosts
        title={"Wirt*innen"}
        addFunction={async (hosts) =>
          await apiClient("http").addHosts(hosts.map((s) => s.id))}
        removeFunction={apiClient("http").removeHosts}
        addToDatabase={database.addHosts}
        removeFromDatabase={database.deleteHosts}
        elements={database.hosts}
        bind:page={hostsPage}
        bind:selectedUnfiltered={hostsSelectedUnfiltered}
        bind:searchInput={hostsSearchInput}
        bind:searchResultsUnfiltered={hostsSearchResultsUnfiltered}
      />
    {:else}
      <Hosts
        title={"Tutor*innen"}
        addFunction={async (tutors) =>
          await apiClient("http").addTutors(tutors.map((s) => s.id))}
        removeFunction={apiClient("http").removeTutors}
        addToDatabase={database.addTutors}
        removeFromDatabase={database.deleteTutors}
        elements={database.tutors}
        bind:page={hostsPage}
        bind:selectedUnfiltered={hostsSelectedUnfiltered}
        bind:searchInput={hostsSearchInput}
        bind:searchResultsUnfiltered={hostsSearchResultsUnfiltered}
      />
    {/if}
  {:else if ui_object.routing.path.main == "anmeldung" && ui_object.routing.path.sub == "wirte"}
    <Hosts
      title={"Wirt*innen für die Stüble-Termine"}
      addFunction={async (hosts) => {
        ui_object.applicationHosts.push(...hosts);
        return hosts;
      }}
      removeFunction={async (hosts) => {
        ui_object.applicationHosts = ui_object.applicationHosts.filter(
          (h) => hosts.findIndex((a) => a == h.id) == -1,
        );
        return true;
      }}
      addToDatabase={async (_) => {}}
      removeFromDatabase={async (_) => {}}
      elements={ui_object.applicationHosts}
      bind:page={hostsPage}
      bind:selectedUnfiltered={hostsSelectedUnfiltered}
      bind:searchInput={hostsSearchInput}
      bind:searchResultsUnfiltered={hostsSearchResultsUnfiltered}
    />
  {/if}
</dialog>

<style>
  #dialog-large {
    padding: 0;
  }
</style>
