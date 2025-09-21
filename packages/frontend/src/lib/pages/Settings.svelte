<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { ui_object, type RouteSettings } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";

  import Button from "$lib/components/Button.svelte";

  $effect(() => {
    // Open dialog
    if (
      (ui_object.path as RouteSettings).sub &&
      ui_object.largeDialog &&
      !ui_object.largeDialog.open
    )
      ui(ui_object.largeDialog);
  });
</script>

<div id="scrollable">
  <p id="header" class="bold">User</p>

  <Button clickable={false}>
    <div>
      <p id="title">Vorname</p>
      <p id="subtitle">
        {ui_object.user?.firstName}
      </p>
    </div>
  </Button>

  <Button clickable={false}>
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
        {ui_object.user ? capitalizeFirstLetter(ui_object.user.residence) : ""}
      </p>
    </div>
  </Button>

  {#if ui_object.capabilities.some((c) => c == "host")}
    <p id="header" class="bold">Administrative Funktionen</p>

    <Button
      onclick={async () =>
        apiClient("http").modifyMotto(
          await ui_object.openEditDialog(
            { title: "Motto", placeholder: "Motto", type: "string" },
            ui_object.motto,
          ),
        )}
    >
      <div>
        <p id="title">Motto</p>
        <p id="subtitle">
          {ui_object.motto}
        </p>
      </div>
    </Button>

    {#if ui_object.capabilities.some((c) => c == "tutor")}
      <Button
        onclick={() => {
          ui_object.changePath({ main: "settings", sub: "hosts" });
        }}
      >
        <div>
          <p id="title">Wirt*innen</p>
          <p id="subtitle">Wirt*innen hinzufügen oder entfernen</p>
        </div>
      </Button>
    {/if}

    {#if ui_object.capabilities.some((c) => c == "admin")}
      <Button
        onclick={async () => {
          if (!ui_object.config) return;

          const res = await apiClient("http").modifyConfig({
            maximumGuests: Number.parseInt(
              await ui_object.openEditDialog(
                {
                  title: "Maximale Personenanzahl",
                  placeholder: "150",
                  type: "number",
                },
                ui_object.config.maximumGuests.toString(),
              ),
            ),
          });

          if (res != null) ui_object.config = res;
        }}
      >
        <div>
          <p id="title">Maximale Personenanzahl</p>
          <p id="subtitle">
            {ui_object.config?.maximumGuests ?? ""}
          </p>
        </div>
      </Button>
    {/if}
  {/if}

  <p id="header" class="bold">Account</p>

  <!-- svelte-ignore a11y_missing_attribute a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <Button
    onclick={async () =>
      (await ui_object.openDialog({ mode: "delete" })) &&
      apiClient("http").deleteAccount(true)}
  >
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
    overflow-x: hidden;
  }

  #header {
    margin: 20px 0 5px 0;
    padding: 0 20px;
    color: var(--secondary);
  }
</style>
