<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { database } from "$lib/lib/database.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Button from "$lib/components/Button.svelte";
  import Fullscreen from "$lib/components/Fullscreen.svelte";
</script>

<Fullscreen header="Wirt*innen" backAction={ui_object.pathBackwards}>
  {#each database.hosts as host}
    <div class="divider"></div>

    <Button
      onclick={async () =>
        (await ui_object.openDialog({ mode: "delete" })) &&
        apiClient("http").removeHosts([host.id])}
    >
      <div>
        <p id="title">
          {host.firstName}
          {host.lastName}
        </p>
      </div>
    </Button>
  {/each}

  {#snippet footerSnippet()}
    <button id="next-button" class="square round extra">
      <i>add</i>
    </button>
  {/snippet}
</Fullscreen>

<style>
  #next-button {
    position: fixed;
    margin: 0;
    bottom: 20px;
    right: 20px;
  }
</style>
