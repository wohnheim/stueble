<script lang="ts">
  import ui from "beercss";
  import { onDestroy, type Snippet } from "svelte";

  let {
    header,
    subheader = "",

    footerVisible = false,
    forceHeaderVisible = false,

    backAction = () => ui("#dialog-large"),

    headerSnippet,
    children,
    footerSnippet,
  }: {
    header: string;
    subheader?: string;

    footerVisible?: boolean;
    forceHeaderVisible?: boolean;

    backAction?: () => void;

    headerSnippet?: Snippet;
    children?: Snippet;
    footerSnippet?: Snippet;
  } = $props();

  let headerVisible = $state(forceHeaderVisible);
  let observer: IntersectionObserver;

  const inViewport = (e: Element) => {
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !forceHeaderVisible) {
          headerVisible = false;
        } else {
          headerVisible = true;
        }
      },
      { rootMargin: "-64px 0px 0px 0px" },
    );

    observer.observe(e);
  };

  onDestroy(() => observer?.disconnect());
</script>

<div id="fullscreen-box">
  <div id="content" class={footerVisible ? "footer" : ""}>
    {#if !forceHeaderVisible}
      <h3 id="header" use:inViewport>{header}</h3>
    {/if}

    {#if children}
      {@render children()}
    {/if}
  </div>

  <div
    id="title-overlay"
    class="row {headerVisible ? 'surface-container' : 'background'}"
  >
    <button id="button" class="transparent circle" onclick={() => backAction()}>
      <i>arrow_back</i>
    </button>

    <div class="transition">
      <div class="transition-overlay" class:show={headerVisible}>
        <p id="title" class={subheader ? "" : "single"}>{header}</p>
        <p id="subtitle">{subheader}</p>
      </div>
    </div>

    {#if headerSnippet !== undefined}
      {@render headerSnippet()}
    {/if}
  </div>

  {#if footerSnippet !== undefined}
    {@render footerSnippet()}
  {/if}
</div>

<style>
  /* Transition */
  .transition {
    height: 64px;
    overflow: hidden;
  }

  .transition-overlay {
    position: relative;
    top: 100%;
    height: 100%;
    transition: all 0.3s ease-out;
  }

  .transition-overlay.show {
    top: 0;
  }

  /* Content-Boxes */
  #fullscreen-box {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  #content {
    padding-top: 64px;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    overflow: auto;
  }

  #content.footer {
    bottom: 80px;
  }

  /* Header-Box */
  #button {
    margin: 8px;
  }

  #title-overlay {
    height: 64px;
    width: 100%;
    margin-top: 0;
    gap: 2px;
    z-index: 1;

    /* Absolute positioning */
    position: absolute;
    left: 0;
    width: 100%;

    padding: 0;
    margin: 0;
  }

  #header {
    margin: 16px 0 30px;
    padding: 0 20px;
  }

  #title {
    font-size: large;
    padding-top: 11px;
    margin: 0;
  }

  #title.single {
    padding-top: 20px;
  }

  #subtitle {
    font-size: small;
    margin-top: -6px;
  }
</style>
