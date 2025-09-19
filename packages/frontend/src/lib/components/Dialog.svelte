<script lang="ts">
  import { onMount } from "svelte";

  import { ui_object } from "$lib/lib/UI.svelte";

  import QrCode from "$lib/dialogs/QRCode.svelte";

  onMount(() =>
    ui_object.generalDialog?.addEventListener("close", () => {
      if (ui_object.dialogProperties.mode !== "unselected")
        setTimeout(() => {
          if (
            ui_object.generalDialog !== undefined &&
            !ui_object.generalDialog.open
          )
            ui_object.dialogProperties.mode = "unselected";
        }, 400); // BeerCSS: --speed3 + 0.1s
    }),
  );
</script>

<dialog
  id="dialog-general"
  bind:this={ui_object.generalDialog}
  style={/* ui_object.dialogProperties.mode == "edit" &&
  (ui_object.dialogProperties.type == "deviceType" ||
    ui_object.dialogProperties.type == "avatar")
    ? "min-height: 250px;"
    : ui_object.dialogProperties.mode == "qrcode"
      ? "width: 357px;"
      : undefined */ undefined}
>
  {#if ui_object.dialogProperties.mode == "qrcode"}
    <QrCode />
  {/if}
</dialog>
