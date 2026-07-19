<script setup>
const props = defineProps({
  status: { type: String, default: 'Starting…' },
  sub: { type: String, default: 'Connecting to Wikipedia…' },
  progress: { type: Number, default: 0 },
  stage: { type: Number, default: 1 },
})

const stages = [
  'Fetch edit history',
  'Build contribution profile',
  'Scan news & trends',
  'Find task gaps',
  'Score & rank tasks',
]

function stageClass(idx) {
  const n = idx + 1
  return { 'is-done': n < props.stage, 'is-active': n === props.stage }
}
</script>

<template>
  <div class="loading-wrap">
    <div class="loading-card">
      <div class="loading-card__spinner" aria-hidden="true"></div>
      <h2 class="loading-card__title">{{ status }}</h2>
      <p class="loading-card__sub">{{ sub }}</p>
      <div class="cdx-progress-bar" role="progressbar" aria-label="Loading progress">
        <div class="cdx-progress-bar__bar" :style="{ width: progress + '%' }"></div>
      </div>
      <ul class="loading-stages">
        <li v-for="(s, i) in stages" :key="i" class="loading-stage" :class="stageClass(i)">{{ s }}</li>
      </ul>
    </div>
  </div>
</template>
