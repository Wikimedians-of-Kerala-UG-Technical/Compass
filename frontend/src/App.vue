<script setup>
import { ref, onMounted, onBeforeUnmount, onErrorCaptured } from 'vue'
import { CdxMessage, CdxButton } from '@wikimedia/codex'
import { useAppStore } from './stores/appStore.js'

const store = useAppStore()
const offline = ref(typeof navigator !== 'undefined' && navigator.onLine === false)
const crashed = ref(false)

const reload = () => window.location.reload()
const setOnline = () => { offline.value = false }
const setOffline = () => { offline.value = true }

onMounted(() => {
  window.addEventListener('online', setOnline)
  window.addEventListener('offline', setOffline)
})
onBeforeUnmount(() => {
  window.removeEventListener('online', setOnline)
  window.removeEventListener('offline', setOffline)
})

// A rendering error in one view shouldn't leave a blank page.
onErrorCaptured((err) => {
  console.error(err)
  crashed.value = true
  return false
})
</script>

<template>
  <CdxMessage v-if="offline" type="warning" class="app-banner" :allow-user-dismiss="false">{{ $t('app.offline') }}</CdxMessage>
  <div v-if="crashed" class="onboard">
    <div class="onboard__card">
      <CdxMessage type="error" :allow-user-dismiss="false">{{ $t('app.crashed') }}</CdxMessage>
      <CdxButton style="margin-top: 16px" @click="reload">{{ $t('app.reload') }}</CdxButton>
    </div>
  </div>
  <RouterView v-else />
</template>
