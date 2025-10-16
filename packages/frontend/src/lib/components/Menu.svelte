<script lang="ts">
  import ui from "beercss";

  import { ui_object } from "$lib/lib/UI.svelte";

  import Logo from "$lib/assets/Stueble-Logo.svelte";
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
        <Logo width={75} />
        <h6>Stüble</h6>
      </nav>
    </header>

    <li
      class="wave round {ui_object.path.main == 'start' ? 'fill' : ''}"
      onclick={() => {
        ui_object.changePath({
          main: "start",
        });
        ui(ui_object.menuDialog);
      }}
    >
      <i>home</i>
      <span>Start</span>
    </li>
    {#if ui_object.capabilities.some((c) => c == "host")}
      <li
        class="wave round {ui_object.path.main == 'wirte' ? 'fill' : ''}"
        onclick={() => {
          ui_object.changePath({
            main: "wirte",
          });
          ui(ui_object.menuDialog);
        }}
      >
        <i>nightlife</i>
        <span>Wirte</span>
      </li>
    {/if}

    <div class="divider"></div>
    <span class="section">Einstellungen</span>

    <li
      class="wave round {ui_object.path.main == 'einstellungen' ? 'fill' : ''}"
      onclick={() => {
        ui_object.changePath({
          main: "einstellungen",
        });
        ui(ui_object.menuDialog);
      }}
    >
      <i>admin_panel_settings</i>
      <span>Einstellungen</span>
    </li>

    <li
      class="wave round"
      onclick={() => {
        ui_object.changePath({
          main: "credits",
        });
        ui(ui_object.menuDialog);
      }}
    >
      <i>star_shine</i>
      <span>Credits</span>
    </li>
  </ul>
</dialog>

<style>
  .section {
    margin: 8px 12px 8px 12px !important;
  }

  .divider {
    margin: 8px 12px 0 12px;
    background-color: var(--on-surface);
  }
</style>
