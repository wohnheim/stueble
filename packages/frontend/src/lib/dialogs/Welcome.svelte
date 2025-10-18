<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
  import { settings } from "$lib/lib/settings.svelte";

  const click = async () => {
    settings.set("welcomeClosed", "true");
    await ui_object.closeDialog(true);
  };
</script>

<h6 id="welcome" class="center-align">Willkommen!</h6>

<div id="properties">
  <div class="row">
    <i class="icon large">event</i>
    <p>In der Regel: Wöchentliches Stüble </p>
  </div>
  <div class="row">
    <i class="icon large">mobile_ticket</i>
    <p>Einfache Anmeldung & Abmeldung </p>
  </div>
  <div class="row">
    <i class="icon large">person_add</i>
    <p>Einladen einer externen Person</p>
  </div>
</div>

<nav id="navigation" class="right-align">
  <button onclick={click}>Start</button>
</nav>

<style>
  .icon {
    margin-right: 15px;
  }

  #welcome {
    margin-bottom: 15px;
  }

  #properties {
    display: flex;
    flex-flow: column;
    gap: 10px;
  }

  #navigation {
    padding-top: 10px;
  }
</style>
