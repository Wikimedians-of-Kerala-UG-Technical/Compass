<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  profile: { type: Object, default: null },
  username: { type: String, default: '' },
  errorMsg: { type: String, default: '' },
})
const emit = defineEmits(['submit'])

const inputValue = ref('')

function submit() {
  emit('submit', inputValue.value)
}

const initials = computed(() => (props.username ? props.username.slice(0, 2).toUpperCase() : '?'))
const topTopics = computed(() => props.profile?.topTopics || [])
const editTypeEntries = computed(() =>
  Object.entries(props.profile?.editTypes || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
)
const recentEdits = computed(() => (props.profile?.recentEdits || []).slice(0, 5))
</script>

<template>
  <div v-if="!profile" class="onboard-wrap">
    <div class="onboard-card">
      <div class="onboard-card__logo">
        <svg viewBox="0 0 60 60" width="60" height="60" aria-hidden="true">
          <circle cx="30" cy="30" r="29" fill="#f8f9fa" stroke="#a2a9b1" stroke-width="1.5" />
          <text
            x="30"
            y="39"
            text-anchor="middle"
            font-family="'Linux Libertine',Georgia,serif"
            font-size="30"
            font-weight="bold"
            fill="#202122"
          >W</text>
        </svg>
      </div>
      <h1 class="onboard-card__heading">Compass</h1>
      <p class="onboard-card__sub">
        Enter your Wikipedia username to discover personalised article editing recommendations.
      </p>

      <div class="cdx-text-input onboard-card__input-wrap">
        <input
          v-model="inputValue"
          class="cdx-text-input__input"
          type="text"
          placeholder="e.g. Ranjithsiji"
          autocapitalize="off"
          autocorrect="off"
          spellcheck="false"
          aria-label="Wikipedia username"
          @keydown.enter="submit"
        />
      </div>

      <button
        class="cdx-button cdx-button--action-progressive cdx-button--weight-primary onboard-card__btn"
        @click="submit"
      >
        Get my recommendations
      </button>

      <div v-if="errorMsg" class="cdx-message cdx-message--error" role="alert">
        <span class="cdx-message__icon"></span>
        <div class="cdx-message__content">{{ errorMsg }}</div>
      </div>
    </div>

    <div class="onboard-features">
      <div class="onboard-feature">
        <div class="onboard-feature__icon">📰</div>
        <div class="onboard-feature__text">
          <strong>Real-time news</strong><br />
          Tasks matched against today's trending events
        </div>
      </div>
      <div class="onboard-feature">
        <div class="onboard-feature__icon">🔍</div>
        <div class="onboard-feature__text">
          <strong>Gap detection</strong><br />
          Find articles missing references, sections, or infoboxes
        </div>
      </div>
      <div class="onboard-feature">
        <div class="onboard-feature__icon">📚</div>
        <div class="onboard-feature__text">
          <strong>Academic sources</strong><br />
          Suggested citations from Semantic Scholar &amp; CrossRef
        </div>
      </div>
    </div>
  </div>

  <section v-else class="wtp-card" aria-label="User profile">
    <div class="wtp-card__header">
      <div class="profile-header">
        <div class="profile-avatar">{{ initials }}</div>
        <div>
          <div class="profile-username">{{ username }}</div>
          <div class="profile-label">Wikipedia contributor</div>
        </div>
      </div>
    </div>

    <div class="profile-stats">
      <div class="profile-stat">
        <span class="profile-stat__num">{{ (profile.total || 0).toLocaleString() }}</span>
        <span class="profile-stat__label">Edits</span>
      </div>
      <div class="profile-stat">
        <span class="profile-stat__num">{{ (profile.uniqueArticles || 0).toLocaleString() }}</span>
        <span class="profile-stat__label">Articles</span>
      </div>
    </div>

    <div v-if="topTopics.length" class="profile-section">
      <div class="profile-section__title">Top topics</div>
      <div class="profile-tags">
        <span v-for="t in topTopics" :key="t" class="wtp-badge wtp-badge--notice" style="margin: 2px">
          {{ t }}
        </span>
      </div>
    </div>

    <div v-if="editTypeEntries.length" class="profile-section">
      <div class="profile-section__title">Edit types</div>
      <div class="profile-tags">
        <span
          v-for="[type, count] in editTypeEntries"
          :key="type"
          class="wtp-badge wtp-badge--neutral"
          style="margin: 2px"
        >
          {{ type }} <strong>{{ count }}</strong>
        </span>
      </div>
    </div>

    <div v-if="recentEdits.length" class="profile-section">
      <div class="profile-section__title">Recent contributions</div>
      <div v-for="(e, i) in recentEdits" :key="i" class="recent-edit">
        <div class="recent-edit__title">
          <a :href="e.articleUrl || '#'" target="_blank" rel="noopener">{{ e.title }}</a>
          <span :class="e.sizediff > 0 ? 'diff-pos' : 'diff-neg'">
            ({{ e.sizediff > 0 ? '+' : '' }}{{ e.sizediff }})
          </span>
          <a v-if="e.diffUrl" :href="e.diffUrl" target="_blank" rel="noopener" class="wtp-badge wtp-badge--neutral">
            diff
          </a>
        </div>
        <div class="recent-edit__meta">{{ e.comment || '(no summary)' }}</div>
      </div>
    </div>
  </section>
</template>
