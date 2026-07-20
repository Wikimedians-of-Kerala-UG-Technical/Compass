<script setup>
import { ref } from 'vue'
import { CdxTextInput, CdxButton, CdxMessage, CdxIcon } from '@wikimedia/codex'
import { cdxIconArticleSearch } from '@wikimedia/codex-icons'
import { useAppStore } from '../stores/appStore.js'

const store = useAppStore()
const inputValue = ref('')

function submit() {
  store.start(inputValue.value)
}
</script>

<template>
  <div class="onboard">
    <div class="onboard__card">
      <div class="onboard__logo">
        <CdxIcon :icon="cdxIconArticleSearch" style="color: var(--color-progressive); width: 48px; height: 48px" />
      </div>
      <h1 class="onboard__heading">Compass</h1>
      <p class="onboard__sub">
        Enter your Wikipedia username to discover personalised editing recommendations — tasks that fit
        your skills, and new articles worth writing in your languages.
      </p>

      <div class="onboard__input">
        <CdxTextInput
          v-model="inputValue"
          placeholder="e.g.Jimbo_Wales"
          aria-label="Wikipedia username"
          @keydown.enter="submit"
        />
      </div>

      <CdxButton class="onboard__btn" action="progressive" weight="primary" @click="submit">
        Get my recommendations
      </CdxButton>

      <CdxMessage v-if="store.onboardError" class="onboard__error" type="error" :allow-user-dismiss="false">
        {{ store.onboardError }}
      </CdxMessage>
    </div>
  </div>
</template>
