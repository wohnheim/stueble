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

  let videoElement = $state<HTMLVideoElement>();
  let codeReader: BrowserQRCodeReader | undefined = undefined;

  onMount(async () => {
    if (properties.type == "qrcode") {
      try {
        // Ask for permission
        const constraints: MediaStreamConstraints = {
          video: { facingMode: "environment" },
        };
        await navigator.mediaDevices.getUserMedia(constraints);

        // Start QRCode reader
        codeReader = new BrowserQRCodeReader();

        await codeReader.decodeFromConstraints(
          constraints,
          videoElement ?? "",
          (result: Result, error?: Exception) => {
            if (!result) return;

            properties.value = result.getText();
            ui_object.closeDialog(true);
          },
        );
      } catch (e) {
        ui_object.closeDialog(false);
      }
    }
  });

  onDestroy(() => {
    if (properties.type == "qrcode" && codeReader !== undefined) {
      codeReader.stopContinuousDecode();
      codeReader.reset();
    }
  });
</script>

<p style="font-size: large; margin-bottom: 2px;">
  {properties.title}
</p>

{#if properties.description !== undefined}
  <p>{properties.description}</p>
{/if}

<div class="field {properties.type == 'textarea' ? 'textarea border' : ''}">
  {#if properties.type == "string"}
    <input
      bind:value={properties.value}
      placeholder={properties.placeholder}
      maxlength={properties.length}
    />
  {:else if properties.type == "textarea"}
    <textarea
      bind:value={properties.value}
      placeholder={properties.placeholder}
      maxlength={properties.length}
    ></textarea>
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
