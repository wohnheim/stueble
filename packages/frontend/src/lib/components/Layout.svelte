<script lang="ts">
  import type { Snippet } from "svelte";

  import { ui_object } from "$lib/lib/UI.svelte";

  import Header from "./Header.svelte";
  import Menu from "./Menu.svelte";
  import Rail from "./Rail.svelte";

  let {
    children,
  }: {
    children?: Snippet;
  } = $props();
</script>

{#if ui_object.layout == "desktop"}
  <Rail />
{:else}
  <Menu />
{/if}

{#if !(ui_object.path.main == "host" && ui_object.path.sub == "list")}
  <Header />
{/if}

<main id="main" class="no-padding responsive">
  {#if children}
    {@render children()}
  {/if}
</main>

{#if ui_object.path.main == "host" && ui_object.path.sub == "list"}
  <button id="add" class="extend square round extra">
    <i>add</i>
    <span>Hinzufügen</span>
  </button>
{/if}

<style>
  #main {
    max-inline-size: none;
  }

  #add {
    position: fixed;
    bottom: 20px;
    right: 20px;

    margin: 0;
  }
</style>
