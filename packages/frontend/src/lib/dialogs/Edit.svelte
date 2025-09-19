<script lang="ts">
  import type { DialogEdit } from "$lib/lib/UI.svelte";

  let {
    properties,
  }: {
    properties: DialogEdit;
  } = $props();
</script>

<p style="font-size: large; margin-bottom: 2px;">
  {properties.title}
</p>

<div class="field">
  {#if properties.type == "string"}
    <input
      bind:value={properties.value}
      placeholder={properties.placeholder}
      maxlength={properties.length}
    />
  {/if}
</div>
