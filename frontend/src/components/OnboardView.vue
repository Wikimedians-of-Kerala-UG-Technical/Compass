<script setup>
import { ref } from 'vue'
import { CdxTextInput, CdxButton, CdxMessage, CdxIcon } from '@wikimedia/codex'
import { cdxIconArticleSearch, cdxIconClose } from '@wikimedia/codex-icons'
import { useAppStore } from '../stores/appStore.js'

const store = useAppStore()
const inputValue = ref('')

function submit() {
  store.open(inputValue.value)
}
</script>

<template>
  <div class="onboard">
    <div class="onboard__card">
      <div class="onboard__logo">
        <CdxIcon :icon="cdxIconArticleSearch" style="color: var(--color-progressive); width: 48px; height: 48px" />
      </div>
      <h1 class="onboard__heading">{{ $t('app.name') }}</h1>
      <p class="onboard__sub">{{ $t('onboard.intro') }}</p>

      <div class="onboard__input">
        <CdxTextInput
          v-model="inputValue"
          :placeholder="$t('onboard.placeholder')"
          :aria-label="$t('onboard.label')"
          @keydown.enter="submit"
        />
      </div>

      <CdxButton class="onboard__btn" action="progressive" weight="primary" @click="submit">
        {{ $t('onboard.submit') }}
      </CdxButton>

      <CdxMessage v-if="store.onboardError" class="onboard__error" type="error" :allow-user-dismiss="false">
        {{ store.onboardError }}
      </CdxMessage>

      <div v-if="store.recent.length" class="onboard__recent">
        <div class="onboard__recent-label">{{ $t('onboard.recent') }}</div>
        <span v-for="name in store.recent" :key="name" class="recent-chip">
          <button class="recent-chip__name" @click="store.open(name)">{{ name }}</button>
          <button class="recent-chip__x" :aria-label="$t('onboard.forget', { name })" @click="store.forget(name)">
            <CdxIcon :icon="cdxIconClose" size="x-small" />
          </button>
        </span>
      </div>

    </div>
  </div>
</template>
