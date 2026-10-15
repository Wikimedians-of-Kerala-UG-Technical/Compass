<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/appStore.js'
import LoadingScreen from './LoadingScreen.vue'
import AppShell from './AppShell.vue'

const store = useAppStore()
const route = useRoute()

watch(() => [route.params.username, route.params.view, route.query.wiki, route.query.article, route.query.articleWiki],
  () => store.syncFromRoute(route), { immediate: true })
</script>

<template>
  <LoadingScreen v-if="store.screen === 'loading'" />
  <AppShell v-else />
</template>
