<script lang="ts">
  import type { MouseEventHandler } from "svelte/elements";

  import { type GuestExtern, type GuestIntern } from "$lib/api/types";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Button from "../Button.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";

  let {
    guest,
    subtitle = "",
    lastSeen = true,
    onclick,
  }: {
    guest: GuestIntern | GuestExtern;
    subtitle?: string;
    lastSeen?: boolean;
    onclick?: MouseEventHandler<HTMLAnchorElement>;
  } = $props();
</script>

<Button {onclick}>
  <div id="inner-row" class="row max no-space">
    <p>{guest.lastName}</p>
    <p>{guest.firstName}</p>
    <p>{!guest.extern ? guest.roomNumber : ""}</p>
    <p>{!guest.extern ? capitalizeFirstLetter(guest.residence) : ""}</p>
  </div>

  <div id="circle" class={guest.present ? "green" : "red"}></div>
</Button>

<style>
  #inner-row > * {
    width: 25%;
  }

  #circle {
    width: 25px;
    height: 25px;

    background-color: var(--tertiary);
    border-radius: 50%;
  }

  .red {
    background-color: red;
  }

  .green {
    background-color: green;
  }
</style>
