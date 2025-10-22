<script lang="ts">
  import type { MouseEventHandler } from "svelte/elements";

  import type { HostOrTutor } from "$lib/api/types";

  import Avatar from "$lib/components/Avatar.svelte";
  import Badge from "$lib/components/Badge.svelte";
  import Button from "$lib/components/Button.svelte";

  let {
    host,
    subtitle = "",
    selected = false,
    onclick,
  }: {
    host: HostOrTutor;
    subtitle?: string;
    selected?: boolean;
    onclick?: MouseEventHandler<HTMLAnchorElement>;
  } = $props();
</script>

<Button {onclick}>
  <div>
    <Avatar residence={host.residence} />

    {#if selected}
      <Badge user />
    {/if}
  </div>

  <div id="host">
    <p id="title">{host.firstName} {host.lastName}</p>
    <p id="subtitle">{subtitle}</p>
  </div>
</Button>

<style>
  #host {
    display: flex;
    flex-flow: column;
  }
</style>
