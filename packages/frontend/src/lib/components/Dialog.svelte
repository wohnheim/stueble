<script lang="ts">
  import { onMount } from "svelte";

  import { ui_object } from "$lib/lib/UI.svelte";

  import Edit from "$lib/dialogs/Edit.svelte";
  import QrCode from "$lib/dialogs/QRCode.svelte";

  onMount(() =>
    ui_object.generalDialog?.addEventListener("close", () => {
      if (ui_object.dialogProperties.mode !== "unselected")
        setTimeout(() => {
          if (ui_object.generalDialog && !ui_object.generalDialog.open)
            ui_object.dialogProperties.mode = "unselected";
        }, 400); // BeerCSS: --speed3 + 0.1s
    }),
  );
</script>

<dialog
  id="dialog-general"
  bind:this={ui_object.generalDialog}
  style={ui_object.dialogProperties.mode == "edit" &&
  ui_object.dialogProperties.type == "qrcode"
    ? "min-height: 500px;"
    : ui_object.dialogProperties.mode == "qrcode"
      ? "width: 357px;"
      : undefined}
>
  {#if ui_object.dialogProperties.mode == "qrcode"}
    <QrCode />
  {:else if ui_object.dialogProperties.mode == "edit"}
    <Edit bind:properties={ui_object.dialogProperties} />
  {/if}
</dialog>
