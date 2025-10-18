<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import { ui_object, type RouteSettings } from "$lib/lib/UI.svelte";
  import { capitalizeFirstLetter } from "$lib/lib/utils";

  import Button from "$lib/components/Button.svelte";
  import { settings } from "$lib/lib/settings.svelte";

  $effect(() => {
    // Open dialog
    if (
      (ui_object.path as RouteSettings).sub &&
      ui_object.largeDialog &&
      !ui_object.largeDialog.open
    )
      ui(ui_object.largeDialog);

    // Close dialog
    if (
      (ui_object.path as RouteSettings).sub === undefined &&
      ui_object.largeDialog &&
      ui_object.largeDialog.open
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
      clickable={ui_object.capabilities.some((c) => c == "tutor")}
      onclick={async () => {
        const motto = await ui_object.openEditDialog(
          {
            title: "Motto dieser Woche",
            description:
              "Ändere das Motto dieser Woche. Dieses Motto wird den Besuchern auf der Anmeldeseite anzeigt und am Morgen nach dem Stüble zurückgesetzt.",
            placeholder: "Motto",
            type: "string",
          },
          settings.settings["motto"],
        );

        if (await apiClient("http").modifyMotto(motto)) {
          await settings.set("motto", motto);
        }
      }}
    >
      <div>
        <p id="title">Motto dieser Woche</p>
        <p id="subtitle">
          {settings.settings["motto"]}
        </p>
      </div>
    </Button>

    <Button
      onclick={async () => {
        const description = await ui_object.openEditDialog(
          {
            title: "Motto-Beschreibung dieser Woche",
            description:
              "Was erwartet die Gäste auf eurer Party (Musik, Specials, Besonderes)? Dieses Nachricht wird den Besuchern auf der Anmeldeseite anzeigt.",
            placeholder: "Beschreibung",
            type: "textarea",
          },
          settings.settings["description"],
        );

        if (await apiClient("http").modifyMotto(undefined, description))
          await settings.set("description", description);
      }}
    >
      <div>
        <p id="title">Motto-Beschreibung dieser Woche</p>
        <p id="subtitle">
          {settings.settings["description"]}
        </p>
      </div>
    </Button>

    {#if ui_object.capabilities.some((c) => c == "tutor")}
      <Button
        onclick={() => {
          ui_object.changePath({ main: "einstellungen", sub: "wirte" });
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
        onclick={() => {
          ui_object.changePath({ main: "einstellungen", sub: "tutoren" });
        }}
      >
        <div>
          <p id="title">Tutor*innen</p>
          <p id="subtitle">Tutor*innen hinzufügen oder entfernen</p>
        </div>
      </Button>

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

          if (res != null) {
            ui_object.config = res;
            await settings.set("config", JSON.stringify(res));
          }
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

  <Button onclick={async () => apiClient("http").logout(true)}>
    <div>
      <p id="title">Abmelden</p>
      <p id="subtitle">Terminiert die aktuelle Session</p>
    </div>
  </Button>

  <!-- Admin accounts can't be deleted -->
  {#if !ui_object.capabilities.some((c) => c == "admin")}
    <Button
      onclick={async () =>
        (await ui_object.openDialog({
          mode: "confirm",
          title: "Confirm deletion",
          confirm: "Delete",
        })) && apiClient("http").deleteAccount(true)}
    >
      <div style="color: red;">
        <p id="title">Account löschen</p>
        <p id="subtitle">Entfernt den Nutzer aus der Datenbank</p>
      </div>
    </Button>
  {/if}
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
