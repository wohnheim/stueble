<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

<!-- svelte-ignore a11y_missing_attribute, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<nav
  class="min left"
  style="z-index: 99; background-color: var(--surface-container);"
>
  <header>
    <a>
      <img class="circle" src="/favicon.svg" draggable="false" alt="Stüble" />
    </a>
  </header>

  <a
    class={ui_object.path.main == "main" ? "active" : ""}
    onclick={() =>
      ui_object.changePath({
        main: "main",
      })}
  >
    <i>home</i>
    <span>Home</span>
  </a>
  {#if ui_object.capabilities.find((c) => c == "host")}
    <a
      class={ui_object.path.main == "host" ? "active" : ""}
      onclick={() =>
        ui_object.changePath({
          main: "host",
        })}
    >
      <i>nightlife</i>
      <span>Wirte</span>
    </a>
  {/if}
  {#if ui_object.capabilities.find((c) => c == "admin")}
    <a
      class={ui_object.path.main == "settings" ? "active" : ""}
      onclick={() =>
        ui_object.changePath({
          main: "settings",
        })}
    >
      <i>admin_panel_settings</i>
      <span>Admin</span>
    </a>
  {/if}
</nav>
