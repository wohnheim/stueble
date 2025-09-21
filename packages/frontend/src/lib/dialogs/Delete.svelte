<script lang="ts">
  import { ui_object } from "$lib/lib/UI.svelte";
</script>

<p style="font-size: large;">Confirm deletion</p>

<nav class="right-align" style="padding: 10px 0 0 0;">
  <button class="transparent link" onclick={() => ui_object.closeDialog()}>
    Cancel
  </button>
  <button class="transparent link" onclick={() => ui_object.closeDialog(true)}>
    Delete
  </button>
</nav>
