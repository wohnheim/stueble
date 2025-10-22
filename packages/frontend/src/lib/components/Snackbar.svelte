<script lang="ts">
  import { error } from "$lib/lib/error";
  import { ui_object } from "$lib/lib/UI.svelte";
  import { onDestroy, onMount } from "svelte";

  const { snackbarError } = error;

  const onClose = () => {
    if ($snackbarError !== false)
      setTimeout(() => {
        if (
          ui_object.snackbarElement &&
          !ui_object.snackbarElement.classList.contains("active")
        )
          $snackbarError = false;
      }, 300); // BeerCSS: --speed2 + 0.1s
  };

  onMount(() => ui_object.snackbarElement?.addEventListener("close", onClose));

  onDestroy(() =>
    ui_object.snackbarElement?.removeEventListener("close", onClose),
  );
</script>

<div
  bind:this={ui_object.snackbarElement}
  class="snackbar {$snackbarError !== false && $snackbarError.error
    ? 'error'
    : ''}"
>
  {#if $snackbarError !== false}
    <i>{$snackbarError.icon}</i>
    <span>{$snackbarError.text}</span>
  {/if}
</div>
