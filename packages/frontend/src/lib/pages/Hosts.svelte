<script lang="ts">
  import { apiClient } from "$lib/api/client";
  import type { HostOrTutor } from "$lib/api/types";
  import { ui_object, WohnheimType } from "$lib/lib/UI.svelte";

  import Button from "$lib/components/Button.svelte";
  import Fullscreen from "$lib/components/Fullscreen.svelte";
  import HostComponent from "$lib/components/buttons/Host.svelte";
  import { findAndRemove } from "$lib/lib/utils";

  let {
    title,
    subtitle = "",
    elements,
    addFunction,
    removeFunction,
    addToDatabase,
    removeFromDatabase,
    page = $bindable(),
    selectedUnfiltered = $bindable(),
    selected,
    searchInput = $bindable(),
    searchResultsUnfiltered = $bindable(),
    searchResults,
  }: {
    title: string;
    subtitle?: string;
    elements: HostOrTutor[];
    addFunction: (ids: string[], date?: Date) => Promise<HostOrTutor[] | null>;
    removeFunction: (ids: string[], date?: Date) => Promise<boolean>;
    addToDatabase: (hosts: HostOrTutor[]) => Promise<void>;
    removeFromDatabase: (ids: string[]) => Promise<void>;
    page: "list" | "add";
    selectedUnfiltered: HostOrTutor[];
    selected: HostOrTutor[];
    searchInput: string;
    searchResultsUnfiltered: HostOrTutor[];
    searchResults: HostOrTutor[];
  } = $props();

  let searchInputElement = $state<HTMLInputElement>();

  const handleKeyDown = (event: KeyboardEvent) => {
    if (!ui_object.largeDialog?.open) return;

    if (event.key === "Enter" && page == "add") {
      if (document.activeElement === searchInputElement) search(searchInput);
      else if (selected.length > 0) add();
    } else if (event.key === "+" && page == "list") {
      page = "add";
    }
  };

  const select = (host: HostOrTutor) => {
    const index = selectedUnfiltered.findIndex((s) => s.id == host.id);
    if (index === -1) selectedUnfiltered.push(host);
    else selectedUnfiltered.splice(index, 1);
  };

  const search = async (input: string) => {
    if (input == "") {
      searchResultsUnfiltered = [];
      return;
    }

    const splitted = input.toLocaleLowerCase().split(" ");

    const roomNumber = findAndRemove(splitted, (s) => Number.isInteger(s));
    const residence = findAndRemove(
      splitted,
      (s) => s == "altbau" || s == "anbau" || s == "neubau" || s == "hirte",
    ) as `${WohnheimType}` | undefined;
    const email = findAndRemove(splitted, (s) => s.includes("@"));

    const query = {
      roomNumber:
        roomNumber !== undefined ? Number.parseInt(roomNumber) : undefined,
      residence,
      email,
    };

    const firstName = findAndRemove(splitted, () => true);
    const lastName = splitted.length > 0 ? splitted[0] : undefined;

    const array = (
      await apiClient("http").searchUsers(
        Object.assign(query, {
          firstName,
          lastName,
        }),
      )
    ).filter((u) => !elements.some((h) => u.id == h.id));

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
            !elements.some((h) => u.id == h.id),
        ),
      );
    }

    searchResultsUnfiltered = array;
  };

  const add = async () => {
    const res = await addFunction(selected.map((s) => s.id));
    if (res != null) await addToDatabase(res);

    selectedUnfiltered = [];
    page = "list";
  };
</script>

<svelte:window on:keydown={handleKeyDown} />

{#if page == "list"}
  <Fullscreen header={title} backAction={ui_object.pathBackwards}>
    {#each elements as element, i}
      {#if i != 0}
        <br />
      {/if}

      <Button
        onclick={async () => {
          if (
            await ui_object.openDialog({
              mode: "confirm",
              title: "Confirm deletion",
              confirm: "Delete",
            })
          ) {
            const res = await removeFunction([element.id]);
            if (res) await removeFromDatabase([element.id]);
          }
        }}
      >
        <div>
          <p id="title">
            {element.firstName}
            {element.lastName}
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
    header={title}
    subheader="Hinzufügen"
    forceHeaderVisible={false}
    backAction={() => (page = "list")}
  >
    <header>
      <div id="search" class="field large round fill">
        <input
          bind:this={searchInputElement}
          placeholder="Suche nach Name, Zimmer oder E-Mail"
          bind:value={searchInput}
        />

        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
        <a id="right-button" class="wave" onclick={() => search(searchInput)}>
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
        <p class="large-text">Keine Nutzer gefunden</p>
      </div>
    {/if}

    {#snippet footerSnippet()}
      <button
        id="next-button"
        class="square round extra"
        disabled={selected.length < 1}
        onclick={add}
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
