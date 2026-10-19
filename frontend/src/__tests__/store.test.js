import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('../router.js', () => ({ router: { push: vi.fn(), replace: vi.fn() } }))
vi.mock('../api.js', () => ({
  sendFeedback: vi.fn(() => Promise.resolve({})),
  clearFeedback: vi.fn(() => Promise.resolve({})),
  getProfile: vi.fn(),
  getTrends: vi.fn(),
  getTasks: vi.fn(),
  getDiscover: vi.fn(),
  getRevisit: vi.fn(),
  getGeo: vi.fn(),
  getContribute: vi.fn(),
  getStats: vi.fn(),
  getFeedback: vi.fn(),
  openAlerts: vi.fn(),
}))

const { useAppStore, urlName } = await import('../stores/appStore.js')
const { router } = await import('../router.js')
const api = await import('../api.js')

describe('app store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('puts usernames in URLs with underscores', () => {
    expect(urlName(' Netha Hussain ')).toBe('Netha_Hussain')
  })

  it('opens a dashboard through the router', () => {
    const store = useAppStore()
    store.open('Netha Hussain', 'mlwiki')
    expect(router.push).toHaveBeenCalledWith({ name: 'dash', params: { username: 'Netha_Hussain' }, query: { wiki: 'mlwiki' } })
    store.open('   ')
    expect(store.onboardError).toBeTruthy()
  })

  it('remembers recent editors, newest first, without duplicates', () => {
    const store = useAppStore()
    for (const n of ['A', 'B', 'A', 'C', 'D', 'E', 'F', 'G']) store.remember(n)
    expect(store.recent).toEqual(['G', 'F', 'E', 'D', 'C', 'A'])
    expect(JSON.parse(localStorage.getItem('compass-recent'))).toEqual(store.recent)
    store.forget('E')
    expect(store.recent).not.toContain('E')
  })

  it('hides voted-down tasks and rolls back a failed vote', async () => {
    const store = useAppStore()
    store.username = 'Tester'
    store.tasks = [{ title: 'A', wiki: 'enwiki' }, { title: 'B', wiki: 'enwiki' }]
    await store.vote(store.tasks[0], 'down')
    expect(store.visibleTasks.map((t) => t.title)).toEqual(['B'])
    api.sendFeedback.mockReturnValueOnce(Promise.reject(new Error('offline')))
    await store.vote(store.tasks[1], 'dismiss')
    expect(store.visibleTasks.map((t) => t.title)).toEqual(['B'])
    expect(store.feedbackError).toBeTruthy()
  })

  it('starts a session only when the user or wiki in the URL changes', () => {
    const store = useAppStore()
    const start = vi.spyOn(store, 'start').mockImplementation(function (u, w) { this.username = u; this.requestedWiki = w })
    store.syncFromRoute({ params: { username: 'Netha_Hussain' }, query: {} })
    store.syncFromRoute({ params: { username: 'Netha_Hussain', view: 'tasks' }, query: {} })
    expect(start).toHaveBeenCalledTimes(1)
    expect(store.activeView).toBe('tasks')
    store.syncFromRoute({ params: { username: 'Netha_Hussain' }, query: { wiki: 'mlwiki' } })
    expect(start).toHaveBeenCalledTimes(2)
  })

  it('loads an article into the Guide from the URL', () => {
    const store = useAppStore()
    vi.spyOn(store, 'start').mockImplementation(function (u) { this.username = u })
    store.syncFromRoute({ params: { username: 'X', view: 'guide' }, query: { article: 'Kochi', articleWiki: 'mlwiki' } })
    expect([store.guideQuery, store.guideWiki, store.guideQuerySeq]).toEqual(['Kochi', 'mlwiki', 1])
    store.syncFromRoute({ params: { username: 'X', view: 'guide' }, query: { article: 'Kochi', articleWiki: 'mlwiki' } })
    expect(store.guideQuerySeq).toBe(1)
  })

  it('undoes votes: clicking again, the undo bar and restoring a server-hidden task', async () => {
    const store = useAppStore()
    store.username = 'Tester'
    store.tasks = [{ title: 'A', wiki: 'enwiki' }]
    store.hiddenTasks = [{ title: 'B', wiki: 'enwiki' }]
    store.feedback = { B: 'down' }
    expect(store.visibleTasks.map((t) => t.title)).toEqual(['A'])
    expect(store.hiddenList.map((h) => [h.title, h.action])).toEqual([['B', 'down']])

    await store.vote(store.tasks[0], 'up')
    await store.vote(store.tasks[0], 'up') // the same vote again takes it back
    expect(store.feedback.A).toBeUndefined()
    expect(api.clearFeedback).toHaveBeenCalledWith('Tester', 'enwiki', 'A')

    await store.vote(store.tasks[0], 'done')
    expect(store.lastHidden).toEqual({ task: store.tasks[0], action: 'done' })
    await store.unvote(store.lastHidden.task)
    expect(store.lastHidden).toBeNull()

    await store.unvote(store.hiddenList[0]) // restore B from the hidden list
    expect(store.visibleTasks.map((t) => t.title)).toEqual(['A', 'B'])
    expect(store.hiddenList).toEqual([])

    api.clearFeedback.mockReturnValueOnce(Promise.reject(new Error('offline')))
    store.feedback = { A: 'dismiss' }
    await store.unvote(store.tasks[0])
    expect(store.feedback.A).toBe('dismiss') // rolled back
    expect(store.feedbackError).toBeTruthy()
  })

  it('offers a correctly capitalised username when the account is missing', async () => {
    const store = useAppStore()
    const err = Object.assign(new Error('No Wikimedia account named "Akash a". Did you mean "Akash A"?'), { suggestion: 'Akash A' })
    api.getProfile.mockReturnValueOnce(Promise.reject(err))
    store.start('Akash a', null)
    await vi.waitFor(() => expect(store.onboardSuggestion).toBe('Akash A'))
    expect(store.onboardError).toContain('Did you mean')
    store.open('Akash A')
    expect(store.onboardSuggestion).toBe('')
  })
})
