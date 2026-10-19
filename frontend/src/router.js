import { createRouter, createWebHistory } from 'vue-router'

// Every screen has a URL, so a refresh keeps you where you were and links can be shared:
//   /u/Ranjithsiji/tasks?wiki=mlwiki       a dashboard view (wiki optional: home wiki)
//   /u/Ranjithsiji/guide?article=കൊച്ചി     the Guide, with an article loaded
//   /event, /event/4579?user=Netha_Hussain   an edit-a-thon's worklist, ranked for one editor
//   /privacy                                what Compass reads and keeps
// The dashboard itself is driven by the store; App.vue keeps the two in sync.
export const VIEWS = ['overview', 'tasks', 'revisit', 'discover', 'contribute', 'guide', 'stats']

export const routes = [
  { path: '/', name: 'onboard', component: () => import('./components/OnboardView.vue') },
  {
    path: '/u/:username/:view?',
    name: 'dash',
    component: () => import('./components/DashboardRoute.vue'),
    beforeEnter: (to) => (to.params.view && !VIEWS.includes(to.params.view) ? { ...to, params: { ...to.params, view: '' } } : true),
  },
  { path: '/event/:id(\\d+)?', name: 'event', component: () => import('./components/EventView.vue') },
  { path: '/privacy', name: 'privacy', component: () => import('./components/PrivacyView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
