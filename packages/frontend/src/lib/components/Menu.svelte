<script lang="ts">
  import ui from "beercss";

  import { ui_object } from "$lib/lib/UI.svelte";
</script>

<!-- Corner radius? -->
<dialog
  class="left small-padding"
  id="dialog-menu"
  bind:this={ui_object.menuDialog}
>
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
  <ul class="list">
    <header>
      <nav>
        <img class="circle" src="/favicon.svg" draggable="false" alt="" />
        <h6>Stüble</h6>
      </nav>
    </header>

    <li
      class="wave round {ui_object.path.main == 'main' ? 'fill' : ''}"
      onclick={() => {
        ui_object.changePath({
          main: "main",
        });
        ui(ui_object.menuDialog);
      }}
    >
      <i>home</i>
      <span>Home</span>
    </li>
    {#if ui_object.capabilities.find((c) => c == "host")}
      <li
        class="wave round {ui_object.path.main == 'host' ? 'fill' : ''}"
        onclick={() => {
          ui_object.changePath({
            main: "host",
          });
          ui(ui_object.menuDialog);
        }}
      >
        <i>nightlife</i>
        <span>Wirte</span>
      </li>
    {/if}

    <div class="divider"></div>
    <span class="section">Settings</span>

    {#if ui_object.capabilities.find((c) => c == "admin")}
      <li
        class="wave round {ui_object.path.main == 'admin' ? 'fill' : ''}"
        onclick={() => {
          ui_object.changePath({
            main: "admin",
          });
          ui(ui_object.menuDialog);
        }}
      >
        <i>admin_panel_settings</i>
        <span>Admin</span>
      </li>
    {/if}
    <li class="wave round">
      <i>help</i>
      <span>Information</span>
    </li>
  </ul>
</dialog>

<style>
  img {
    height: 40px;
    width: 40px;
  }

  .section {
    margin: 8px 12px 8px 12px !important;
  }

  .divider {
    margin: 8px 12px 0 12px;
    background-color: var(--on-surface);
  }
</style>
