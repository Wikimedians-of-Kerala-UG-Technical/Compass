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
        Finding your home wiki and reading your recent edits and the topics of the articles you work on.
        Usually 10–30 seconds. Tasks and suggestions load in the background once you're in.
      </p>
    </div>
  </div>
</template>
