<script lang="ts">
  import * as materialSymbols from "beercss/dist/cdn/material-symbols-outlined.woff2";
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