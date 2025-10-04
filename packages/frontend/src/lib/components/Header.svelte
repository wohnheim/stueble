<script lang="ts">
  import ui from "beercss";

  import { ui_object } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";
  import { settings } from "$lib/lib/settings.svelte";
</script>

<header>
  <nav>
    {#if ui_object.layout == "mobile"}
      <button
        class="circle transparent"
        onclick={() => ui(ui_object.menuDialog)}
      >
        <i>menu</i>
        <div class="tooltip bottom">Menü</div>
      </button>
    {/if}

    {#if ui_object.path.main == "start" && ui_object.path.sub == "einladen"}
      <button class="circle transparent" onclick={ui_object.pathBackwards}>
        <i>arrow_back</i>
        <div class="tooltip bottom">Zurück</div>
      </button>
    {/if}

    {#if ui_object.layout == "mobile"}
      <p style="font-size: large; font-weight: 600;">
        {capitalizeFirstLetter(ui_object.path.main)}
      </p>
    {/if}

    {#if ui_object.layout == "desktop" && settings.settings["motto"] !== undefined}
      <div id="centered-title" class="row">
        <p>✨</p>

        <p class="bold">
          Motto: <span class="secondary-text">{settings.settings["motto"]}</span
          >
        </p>

        {#if ui_object.status?.date !== undefined}
          <p>✨</p>

          <p class="bold">
            Datum: <span class="secondary-text"
              >{ui_object.status.date.toLocaleDateString("de-DE")}</span
            >
          </p>
        {/if}

        <p>✨</p>
      </div>
    {/if}
  </nav>
</header>

<style>
  #centered-title {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

    margin: 0;
  }
</style>
