<script lang="ts">
  import dayjs from "dayjs";
  import type { MouseEventHandler } from "svelte/elements";

  import type { IDevices } from "$lib/lib/fetchers";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Badge from "../Badge.svelte";
  import Button from "../Button.svelte";

  let {
    device,
    subtitle = "",
    lastSeen = false,
    selected = false,
    onclick,
  }: {
    device: IDevices["self"] & { online?: boolean };
    subtitle?: string;
    lastSeen?: boolean;
    selected?: boolean;
    onclick?: MouseEventHandler<HTMLAnchorElement>;
  } = $props();
</script>

<Button {onclick}>
  <div id="circle" class={device.online ? "green-border" : undefined}>
    <i class="small"
      >{device.type == "desktop"
        ? "desktop_mac"
        : device.type == "tablet"
          ? "tablet_mac"
          : device.type == "phone"
            ? "phone_iphone"
            : "laptop_mac"}</i
    >

    {#if selected}
      <Badge />
    {/if}
  </div>

  <div>
    <p id="title">{device.display_name}</p>
    <p id="subtitle">
      {subtitle
        ? subtitle
        : `Created at ${dayjs.unix(device.created_at).format("HH:mm, DD.MM.YYYY")}.`}
    </p>
  </div>

  {#if lastSeen}
    <div class="max"></div>
    <div id="last-seen" class="bold">
      {#await ui_object.getLastSend("device", device.did) then lastSend}
        {lastSend}
      {/await}
    </div>
  {/if}
</Button>

<style>
  #circle {
    width: 45px;
    height: 45px;

    line-height: 35px;
    text-align: center;
    font-size: large;

    position: relative;

    border: 5px solid var(--tertiary);
    border-radius: 50%;
  }

  #last-seen {
    font-size: small;
    padding-bottom: 18px;
  }
</style>
