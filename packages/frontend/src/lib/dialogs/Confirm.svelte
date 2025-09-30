<script lang="ts">
  import { ui_object, type DialogConfirm } from "$lib/lib/UI.svelte";

  let {
    properties = $bindable(),
  }: {
    properties: DialogConfirm;
  } = $props();
</script>

<p style="font-size: large;">{properties.title}</p>

{#if properties.description !== undefined}
  <p>{properties.description}</p>
{/if}

<nav class="right-align" style="padding: 10px 0 0 0;">
  <button class="transparent link" onclick={() => ui_object.closeDialog()}>
    {properties.cancel === undefined ? "Cancel" : properties.cancel}
  </button>
  <button class="transparent link" onclick={() => ui_object.closeDialog(true)}>
    {properties.confirm === undefined ? "Confirm" : properties.confirm}
  </button>
</nav>
