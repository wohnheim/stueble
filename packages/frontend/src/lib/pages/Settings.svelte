<script lang="ts">
  import ui from "beercss";
  import dayjs from "dayjs";
  import { nanoid } from "nanoid";

  import { apiClient } from "$lib/api/client";
  import { ui_object, type RouteSettings } from "$lib/lib/UI.svelte";

  import Button from "$lib/components/Button.svelte";

  $effect(() => {
    // Open dialog
    if (
      ui_object.layout == "mobile" &&
      (ui_object.path as RouteSettings).sub &&
      ui_object.largeDialog &&
      !ui_object.largeDialog.open
    )
      ui("#dialog-large");

    // Close dialogs
    if (
      (ui_object.layout == "desktop" ||
        !(ui_object.path as RouteSettings).sub) &&
      ui_object.largeDialog &&
      ui_object.largeDialog.open
    )
      ui("#dialog-large");
    if (
      ui_object.layout == "desktop" &&
      ui_object.dialogProperties.mode == "edit" &&
      ui_object.generalDialog?.open
    )
      ui_object.closeDialog();
  });
</script>

<div id="scrollable">
  <p id="header" class="bold">User</p>

  <Button
    onclick={async () =>
      ui_object.user !== undefined &&
      apiClient("http").modifyUser({
        id: ui_object.user.id,
        firstName: await ui_object.openEditDialog(
          { title: "Vorname", placeholder: "Vorname", type: "string" },
          ui_object.user.firstName,
        ),
      })}
  >
    <div>
      <p id="title">Vorname</p>
      <p id="subtitle">
        {ui_object.user?.firstName}
      </p>
    </div>
  </Button>

  <Button
    onclick={async () =>
      ui_object.user !== undefined &&
      apiClient("http").modifyUser({
        id: ui_object.user.id,
        lastName: await ui_object.openEditDialog(
          { title: "Nachname", placeholder: "Nachname", type: "string" },
          ui_object.user.lastName,
        ),
      })}
  >
    <div>
      <p id="title">Nachname</p>
      <p id="subtitle">
        {ui_object.user?.lastName}
      </p>
    </div>
  </Button>

  <Button clickable={false}>
    <div>
      <p id="title">Zimmernummer</p>
      <p id="subtitle">
        {ui_object.user?.roomNumber}
      </p>
    </div>
  </Button>

  <Button clickable={false}>
    <div>
      <p id="title">Wohnheim</p>
      <p id="subtitle">
        {ui_object.user?.residence}
      </p>
    </div>
  </Button>

  {#if ui_object.capabilities.some((c) => c == "host")}
    <p id="header" class="bold">Administrative Funktionen</p>

    <Button>
      <div>
        <p id="title">Motto</p>
        <p id="subtitle">
          {ui_object.motto}
        </p>
      </div>
    </Button>

    <Button clickable={false}>
      <div>
        <p id="title">Maximale Personenanzahl</p>
        <p id="subtitle">
          {150}
        </p>
      </div>
    </Button>
  {/if}

  <p id="header" class="bold">Devices</p>

  <Button>
    <div>
      <p id="title">Devices</p>
      <p id="subtitle">Manage devices</p>
    </div>
  </Button>

  <p id="header" class="bold">Account</p>

  <!-- svelte-ignore a11y_missing_attribute a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <Button onclick={() => apiClient("http").deleteAccount(true)}>
    <div style="color: red;">
      <p id="title">Delete account</p>
      <p id="subtitle">Removes user from database</p>
    </div>
  </Button>
</div>

<style>
  #scrollable {
    height: 100%;
    overflow-y: auto;
  }

  #header {
    margin: 20px 0 5px 0;
    padding: 0 20px;
    color: var(--secondary);
  }
</style>
