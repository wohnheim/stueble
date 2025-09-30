<script lang="ts">
  import ui from "beercss";

  import { ui_object } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";
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

    {#if ui_object.path.main == "main" && ui_object.path.sub == "invitation"}
      <button class="circle transparent" onclick={ui_object.pathBackwards}>
        <i>arrow_back</i>
        <div class="tooltip bottom">Zurück</div>
      </button>
    {/if}

    {#if ui_object.layout == "mobile"}
      <p style="font-size: large; font-weight: 600;">
        {capitalizeFirstLetter(
          ui_object.path.main == "main" ? "home" : ui_object.path.main,
        )}
      </p>
    {/if}

    <div class="max"></div>
  </nav>
</header>
