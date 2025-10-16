<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

{#snippet creditSnippet()}
  <p>
    Das Haus-Edith-Stein- und das Hirten-Logo wurden von Sina Dippel erstellt.
    🎨 🖌️<br />
    Vielen Dank!
  </p>

  <p>
    Erstellung und Administration der Webseite von Quentin Frey und Leon
    Gattermeyer. 🖥️ ☁️
  </p>

  <h6>Support</h6>

  <p>
    Bei Problemen wende dich an diese E-Mail: <a
      href="mailto:tutorenhes@gmail.com">tutorenhes@gmail.com</a
    >
  </p>
{/snippet}

{#if ui_object.layout == "desktop"}
  <article class="center middle absolute middle-align center-align border">
    <div>
      <h6>Credits</h6>

      {@render creditSnippet()}
    </div>
  </article>
{:else}
  {@render creditSnippet()}
{/if}
