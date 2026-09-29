<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

{#snippet musikraumSnippet(layout: (typeof ui_object)["layout"])}
  {#if layout == "desktop"}
    <h6>Musikraum</h6>
  {:else}
    <p class="large-text bold">Musikraum</p>
  {/if}

  <p>Auf der Website wird angezeigt, ob der Musikraum belegt ist.</p>

  <p>
    <span class="secondary-text bold">Eine Reservierung ist nicht möglich</span
    >, da der Musikraum für HESler und Hirten zum spontanen Proben und
    Musizieren gedacht ist.
  </p>

  <p>
    Einzige Ausnahme sind Auftritte für HES, ZGH oder KHG. Hierfür kann der
    Musikraum unter Absprache mit den Tutoren und/oder der KHG bis zum Auftritt
    für Proben reserviert werden.
  </p>

  {#if layout == "desktop"}
    <h6>Link zur Webseite</h6>
  {:else}
    <p class="large-text bold">Link zur Webseite</p>
  {/if}

  <p>
    <a class="tertiary-text" href="https://musikraum.onrender.com">
      https://musikraum.onrender.com
    </a>
  </p>

  <p>
    Passwort: <span class="secondary-text bold">Make some NOISE</span>
  </p>
{/snippet}

{#if ui_object.layout == "desktop"}
  <article class="center middle absolute middle-align center-align border">
    <div>
      {@render musikraumSnippet(ui_object.layout)}
    </div>
  </article>
{:else}
  <div class="large-padding center-align">
    {@render musikraumSnippet(ui_object.layout)}
  </div>
{/if}
