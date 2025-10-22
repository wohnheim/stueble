<script lang="ts">
  import type { HostOrTutor } from "$lib/api/types";

  import HES from "$lib/assets/HES.svg";
  import ZGH from "$lib/assets/ZGH.svg";

  let {
    residence,
  }: {
    residence: HostOrTutor["residence"];
  } = $props();
</script>

<img
  id="avatar"
  class="circle medium"
  src={residence == "hirte" ? ZGH : HES}
  style="height: 45px; width: 45px;"
  alt="Avatar"
  draggable="false"
/>

<style>
  #avatar {
    max-inline-size: none;
    max-block-size: none;
  }
</style>
