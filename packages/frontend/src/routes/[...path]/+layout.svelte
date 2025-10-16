<script lang="ts">
  import { browser } from "$app/environment";
  import { page } from "$app/state";
  import { onMount, type Snippet } from "svelte";
  import { quadOut } from "svelte/easing";
  import { get } from "svelte/store";
  import { fade } from "svelte/transition";

  import ui from "beercss";
  import * as materialSymbols from "beercss/dist/cdn/material-symbols-outlined.woff2";

  import { apiClient } from "$lib/api/client";
  import { error } from "$lib/lib/error";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Logo from "$lib/assets/Stueble.svelte";
  import Layout from "$lib/components/Layout.svelte";
  import Dialog from "$lib/components/Dialog.svelte";
  import LargeDialog from "$lib/components/LargeDialog.svelte";
  import Snackbar from "$lib/components/Snackbar.svelte";

  let {
    children,
  }: {
    children?: Snippet;
  } = $props();

  const { error: errorStore, overlay } = error;

  let offlineInterval: ReturnType<typeof setInterval> | undefined = undefined;

  onMount(async () => {
    if (browser) {
      if (!navigator.onLine) error.offline();

      const continueMount = () => {
        $errorStore = false;

        window.addEventListener("online", () => {
          apiClient("ws")
            .checkConnection()
            .then((v) => v && error.solved());
        });
        window.addEventListener("offline", () => {
          ui_object.closeDialog();
          if (ui_object.largeDialog?.open) ui(ui_object.largeDialog);

          if (offlineInterval === undefined) {
            offlineInterval = setInterval(async () => {
              if (
                navigator.onLine &&
                (await apiClient("ws").checkConnection())
              ) {
                clearInterval(offlineInterval);
                offlineInterval = undefined;
                error.solved();
              }
            }, 1000);
          }

          error.offline();
        });
      };

      if (localStorage.getItem("loggedIn") == "true") {
        if (get(apiClient("ws").connected)) continueMount();
        else {
          const unsubscribe = apiClient("ws").connected.subscribe(
            async (connected) => {
              if (connected) {
                unsubscribe();
                continueMount();
              }
            },
          );
        }
      }
    }
  });

  $effect(() => {
    if (browser)
      ui_object.path = ui_object.getPath(location.pathname, page.url.pathname);
  });
</script>

<svelte:head>
  <link
    rel="preload"
    as="font"
    href={materialSymbols.default}
    type="font/woff2"
    crossorigin="anonymous"
  />
</svelte:head>

{#if !$overlay}
  <div
    id="overlay"
    in:fade={{ duration: 200 }}
    out:fade={{ delay: 200, duration: 1000, easing: quadOut }}
  ></div>

  <div
    id="logo"
    class={$overlay}
    in:fade={{ duration: 200 }}
    out:fade={{ delay: 200, duration: 1000, easing: quadOut }}
  >
    <Logo />
  </div>

  <div
    id="offline"
    class="center-align"
    in:fade={{ duration: 200 }}
    out:fade={{ delay: 200, duration: 1000, easing: quadOut }}
  >
    {#if $errorStore !== false}
      <i class="extra">{$errorStore.icon}</i>
      <p class="large-text">{$errorStore.text}</p>
    {/if}
  </div>
{/if}

<div id="overlay" class={$overlay}></div>

{#if $overlay}
  <!-- Dialogs -->
  {#if ui_object.path.main == "einstellungen"}
    <LargeDialog />
  {/if}
  <Dialog />
  <Snackbar />

  <Layout>
    {#if children}
      {@render children()}
    {/if}
  </Layout>
{/if}

<style>
  .hidden {
    display: none !important;
    opacity: 0;
    z-index: -1 !important;
  }

  #overlay {
    position: absolute;
    z-index: 10000;
    width: 100%;
    height: 100%;

    background: var(--background);
  }

  #logo {
    position: absolute;
    z-index: 10001;
    width: 100%;
    height: 50%;
    top: 0;

    display: flex;
    justify-content: center;
    align-items: center;
  }

  #offline {
    position: absolute;
    z-index: 10001;
    width: 100%;
    height: 50%;
    bottom: 0;
  }
</style>
