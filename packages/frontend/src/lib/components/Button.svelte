<script lang="ts">
  import type { Snippet } from "svelte";
  import type { MouseEventHandler } from "svelte/elements";

  let {
    clickable = true,
    onclick,
    children,
  }: {
    clickable?: boolean;
    onclick?: MouseEventHandler<HTMLAnchorElement>;
    children?: Snippet;
  } = $props();
</script>

{#if clickable}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <a id="common" class="chip border responsive row" {onclick}>
    {#if children}
      {@render children()}
    {/if}
  </a>
{:else}
  <div id="common" class="notClickable row">
    {#if children}
      {@render children()}
    {/if}
  </div>
{/if}

<style>
  #common {
    margin: 0;
    padding: 11px 20px;
    border: 0;
    color: var(--on-background);
  }

  #common.notClickable {
    height: 70px;
    padding: 0 20px;

    line-height: normal;
  }

  #common {
    & :global(#title) {
      font-size: large;
    }

    & :global(#subtitle) {
      font-size: small;
      margin-top: -0.5rem;
    }
  }
</style>
