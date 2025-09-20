<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import {
    BrowserQRCodeReader,
    type Exception,
    type Result,
  } from "@zxing/library";

  import { ui_object, type DialogEdit } from "$lib/lib/UI.svelte";

  let {
    properties = $bindable(),
  }: {
    properties: DialogEdit;
  } = $props();

  const decode = async (
    codeReader: BrowserQRCodeReader,
    selectedDeviceId: string,
  ) => {
    codeReader.decodeFromVideoDevice(
      selectedDeviceId,
      videoElement ?? null,
      (result: Result, error?: Exception) => {
        if (!result) return;

        properties.value = result.getText();
        ui_object.closeDialog(true);
      },
    );
  };

  let videoElement = $state<HTMLVideoElement>();
  let codeReader: BrowserQRCodeReader | undefined = undefined;

  onMount(async () => {
    if (properties.type == "qrcode") {
      codeReader = new BrowserQRCodeReader();

      const devices = await codeReader.listVideoInputDevices();
      const selectedDeviceId = devices[0]?.deviceId;

      if (selectedDeviceId !== undefined) decode(codeReader, selectedDeviceId);
    }
  });

  onDestroy(() => {
    if (properties.type == "qrcode") {
      codeReader?.reset();
    }
  });
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
  {:else if properties.type == "number"}
    <input
      bind:value={properties.value}
      placeholder={properties.placeholder}
      type="number"
    />
  {:else if properties.type == "qrcode"}
    <!-- svelte-ignore a11y_media_has_caption -->
    <video bind:this={videoElement} width="300" height="400"></video>
  {/if}
</div>
