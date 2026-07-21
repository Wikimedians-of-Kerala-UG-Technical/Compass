<script setup>
import { CdxProgressBar } from '@wikimedia/codex'
import { useAppStore } from '../stores/appStore.js'

const store = useAppStore()
</script>

<template>
  <div class="loading-screen" role="main" aria-live="polite">
    <div class="loading-screen__card">
      <CdxProgressBar aria-label="Loading" />
      <h2 class="loading-screen__title">Loading {{ store.username }}'s profile…</h2>
      <p class="loading-screen__sub">
        Fetching edit history — this can take a minute or two for accounts with a lot of edits. Trends,
        tasks, and article suggestions will load in the background once you're in.
      </p>
    </div>
  </div>
</template>
