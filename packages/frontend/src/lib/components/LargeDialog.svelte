<script lang="ts">
  import { onMount } from "svelte";

  import { ui_object } from "$lib/lib/UI.svelte";
  import Hosts from "$lib/pages/Hosts.svelte";

  let groupPropertiesPage: "main" | "members" | "requests" | "add" =
    $state("main");

  let groupCreatePage: "add" | "name" = $state("add");
  let groupCreateSelected: {
    uid: number;
    avatar_seed: string;
    display_name: string;
  }[] = $state([]);
  let groupCreateName = $state("");

  onMount(() => {
    ui_object.largeDialog?.addEventListener("close", () => {
      if (
        ui_object.layout == "mobile" &&
        ui_object.path.main == "settings" // &&
        // ui_object.path.sub !== undefined
      )
        ui_object.changePath({ main: "settings" });

      if (groupPropertiesPage)
        setTimeout(() => (groupPropertiesPage = "main"), 400);

      if (groupCreatePage)
        setTimeout(() => {
          groupCreatePage = "add";
          groupCreateSelected = [];
          groupCreateName = "";
        }, 400);
    });
  });
</script>

<dialog id="dialog-large" bind:this={ui_object.largeDialog} class="right large">
  {#if ui_object.path.main == "settings"}
    <Hosts />
  {/if}
</dialog>

<style>
  #dialog-large {
    padding: 0;
  }
</style>
