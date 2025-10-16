<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

{#snippet creditSnippet(layout: (typeof ui_object)["layout"])}
  {#if layout == "desktop"}
    <h6>Credits</h6>
  {:else}
    <p class="large-text bold">Credits</p>
  {/if}

  <p>
    Die Logos der Wohnheime wurden von <span class="secondary-text bold"
      >Sina Dippel</span
    >
    erstellt. 🎨 🖌️ Vielen Dank!
  </p>

  <p>
    Erstellung und Administration der Webseite von <span
      class="secondary-text bold">Quentin Frey</span
    >
    und <span class="secondary-text bold">Leon Gattermeyer</span>. 🖥️ ☁️
  </p>

  {#if layout == "desktop"}
    <h6>Support</h6>
  {:else}
    <p class="large-text bold">Support</p>
  {/if}

  <p>
    Bei Problemen wende dich an diese E-Mail: <a
      class="tertiary-text"
      href="mailto:tutorenhes@gmail.com">tutorenhes@gmail.com</a
    >
  </p>
{/snippet}

{#if ui_object.layout == "desktop"}
  <article class="center middle absolute middle-align center-align border">
    <div>
      {@render creditSnippet(ui_object.layout)}
    </div>
  </article>
{:else}
  <div class="large-padding center-align">
    {@render creditSnippet(ui_object.layout)}
  </div>
{/if}
