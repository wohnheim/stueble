<script lang="ts">
  import { fade } from "svelte/transition";

  let { user = false } = $props();
</script>

<div
  id="badge-wrapper"
  class={user ? "contact" : ""}
  transition:fade={{ duration: 150 }}
>
  <div id="overlay-circle"></div>

  <div id="badge">
    <i>check</i>
  </div>
</div>

<style>
  #badge-wrapper {
    position: absolute;

    top: 20px;
    left: 20px;
  }

  #badge-wrapper.contact {
    top: 25px;
    left: 25px;
  }

  #overlay-circle {
    height: 26px;
    width: 26px;

    position: absolute;

    border-radius: 50%;
    background-color: var(--background);
  }

  #badge {
    width: 22px;
    height: 22px;

    z-index: 1;
    position: absolute;
    left: 2px;
    top: 2px;

    display: flex;
    justify-content: center;

    border-radius: 50%;
    background-color: var(--error);
    color: var(--on-error);
  }

  #badge > i {
    ---size: 1.2rem;
  }
</style>
