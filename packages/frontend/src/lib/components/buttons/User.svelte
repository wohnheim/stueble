<script lang="ts">
  import type { MouseEventHandler } from "svelte/elements";

  import { getDicebearUrl } from "../../../../../common/common";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Badge from "../Badge.svelte";
  import Button from "../Button.svelte";

  let {
    user,
    subtitle = "",
    lastSeen = false,
    selected = false,
    onclick,
  }: {
    user: { uid: number; avatar_seed: string; display_name: string };
    subtitle?: string;
    lastSeen?: boolean;
    selected?: boolean;
    onclick?: MouseEventHandler<HTMLAnchorElement>;
  } = $props();
</script>

<Button {onclick}>
  <div>
    <img
      class="circle medium"
      src={getDicebearUrl(user.avatar_seed)}
      style="height: 45px; width: 45px;"
      alt="Avatar"
      draggable="false"
    />

    {#if selected}
      <Badge user />
    {/if}
  </div>

  <div>
    <p id="title">{user.display_name}</p>
    <p id="subtitle">{subtitle}</p>
  </div>

  {#if lastSeen}
    <div class="max"></div>
    <div id="last-seen" class="bold">
      {#await ui_object.getLastSend("contact", user.uid) then lastSend}
        {lastSend}
      {/await}
    </div>
  {/if}
</Button>

<style>
  #last-seen {
    font-size: small;
    padding-bottom: 18px;
  }
</style>
