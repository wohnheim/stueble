<script lang="ts">
  import type { MouseEventHandler } from "svelte/elements";

  import type { HostOrTutor } from "$lib/api/types";

  import Badge from "../Badge.svelte";
  import Button from "../Button.svelte";

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
    <img
      class="circle medium"
      style="height: 45px; width: 45px;"
      alt="Avatar"
      draggable="false"
    />

    {#if selected}
      <Badge user />
    {/if}
  </div>

  <div>
    <p id="title">{host.firstName} {host.lastName}</p>
    <p id="subtitle">{subtitle}</p>
  </div>
</Button>
