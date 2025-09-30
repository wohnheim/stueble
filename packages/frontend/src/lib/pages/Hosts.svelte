<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import type { Host } from "$lib/api/types";
  import { database } from "$lib/lib/database.svelte";
  import { ui_object } from "$lib/lib/UI.svelte";

  import Button from "$lib/components/Button.svelte";
  import Fullscreen from "$lib/components/Fullscreen.svelte";
  import HostComponent from "$lib/components/buttons/Host.svelte";

  let {
    page = $bindable(),
    selectedUnfiltered = $bindable(),
    selected = $bindable(),
    searchInput = $bindable(),
    searchResultsUnfiltered = $bindable(),
    searchResults = $bindable(),
  }: {
    page: "list" | "add";
    selectedUnfiltered: Host[];
    selected: Host[];
    searchInput: string;
    searchResultsUnfiltered: Host[];
    searchResults: Host[];
  } = $props();

  const select = (host: Host) => {
    const index = selectedUnfiltered.findIndex((s) => s.id == host.id);
    if (index === -1) selectedUnfiltered.push(host);
    else selectedUnfiltered.splice(index, 1);

    selectedUnfiltered = selectedUnfiltered;
  };

  const search = async (input: string) => {
    const splitted = input.split(" ");

    const roomNumber = splitted.find((s) => Number.isInteger(s));
    const residence = splitted.find(
      (s) => s == "hirte" || s == "altbau" || s == "anbau" || s == "neubau",
    );
    const email = splitted.find((s) => s.includes("@"));

    const query = {
      roomNumber:
        roomNumber !== undefined ? Number.parseInt(roomNumber) : undefined,
      residence,
      email,
    };

    const firstName = splitted.find(
      (s) => s != roomNumber && s != residence && s != email,
    );

    const lastName = splitted.find(
      (s) => s != roomNumber && s != residence && s != email && s != firstName,
    );

    const array = (
      await apiClient("http").searchUsers(
        Object.assign(query, {
          firstName,
          lastName,
        }),
      )
    ).filter((u) => !database.hosts.some((h) => u.id == h.id));

    if (firstName !== undefined && lastName === undefined) {
      array.push(
        ...(
          await apiClient("http").searchUsers(
            Object.assign(query, {
              lastName: firstName,
            }),
          )
        ).filter(
          (u) =>
            !array.some((u1) => u.id == u1.id) &&
            !database.hosts.some((h) => u.id == h.id),
        ),
      );
    }

    return array;
  };
</script>

{#if page == "list"}
  <Fullscreen header="Wirt*innen" backAction={ui_object.pathBackwards}>
    {#each database.hosts as host, i}
      {#if i != 0}
        <br />
      {/if}

      <Button
        onclick={async () =>
          (await ui_object.openDialog({
            mode: "confirm",
            title: "Confirm deletion",
            confirm: "Delete",
          })) && apiClient("http").removeHosts([host.id])}
      >
        <div>
          <p id="title">
            {host.firstName}
            {host.lastName}
          </p>
        </div>
      </Button>
    {/each}

    {#snippet footerSnippet()}
      <button
        id="next-button"
        class="square round extra"
        onclick={() => (page = "add")}
      >
        <i>add</i>
      </button>
    {/snippet}
  </Fullscreen>
{:else}
  <Fullscreen
    header="Wirt*innen"
    subheader="Hinzufügen"
    forceHeaderVisible={false}
    backAction={() => (page = "list")}
  >
    <header>
      <div id="search" class="field large round fill">
        <input placeholder="Search for guests" bind:value={searchInput} />

        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <a
          id="right-button"
          class="wave"
          onclick={() => {
            if (searchInput == "") searchResultsUnfiltered = [];
            else
              search(searchInput).then(
                (res) => (searchResultsUnfiltered = res),
              );
          }}
        >
          <i>search</i>
        </a>
      </div>
    </header>

    {#each selected as host}
      <HostComponent {host} selected={true} onclick={() => select(host)} />
    {/each}

    {#each searchResults.filter((r) => !selected.some((s) => s.id == r.id)) as host}
      <HostComponent {host} selected={false} onclick={() => select(host)} />
    {/each}

    {#if selected.length === 0 && searchResults.length === 0}
      <div class="center-align">
        <p class="large-text">No users found</p>
      </div>
    {/if}

    {#snippet footerSnippet()}
      <button
        id="next-button"
        class="square round extra"
        disabled={selected.length < 1}
        onclick={async () => {
          await apiClient("http").addHosts(selected.map((s) => s.id));
          page = "list";
        }}
      >
        <i>check</i>
      </button>
    {/snippet}
  </Fullscreen>
{/if}

<style>
  .field {
    margin-block-start: 8px;
    margin-block-end: 8px;
  }

  #search.field > a#right-button {
    inset: 50% 0.4rem auto auto;
  }

  #right-button {
    block-size: 2.5rem;
    inline-size: 2.5rem;
    z-index: 1;
  }

  #next-button {
    position: fixed;
    margin: 0;
    bottom: 20px;
    right: 20px;
  }
</style>
