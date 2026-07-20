<script setup>
import { useAppStore } from './stores/appStore.js'
import OnboardView from './components/OnboardView.vue'
import LoadingScreen from './components/LoadingScreen.vue'
import AppShell from './components/AppShell.vue'

const store = useAppStore()
</script>

<template>
  <OnboardView v-if="store.screen === 'onboard'" />
  <LoadingScreen v-else-if="store.screen === 'loading'" />
  <AppShell v-else />
</template>
