import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import ClubsView from '../views/ClubsView.vue'
import MembersView from '../views/MembersView.vue'
import ActivitiesView from '../views/ActivitiesView.vue'
import FinanceView from '../views/FinanceView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import ReportsView from '../views/ReportsView.vue'
import AccountsView from '../views/AccountsView.vue'
import AppLayout from '../components/AppLayout.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  {
    path: '/', component: AppLayout,
    children: [
      { path: '', name: 'dashboard', component: DashboardView },
      { path: 'clubs', component: ClubsView },
      { path: 'members', component: MembersView },
      { path: 'activities', component: ActivitiesView },
      { path: 'finance', component: FinanceView },
      { path: 'notifications', component: NotificationsView },
      { path: 'reports', component: ReportsView },
      { path: 'accounts', component: AccountsView },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return auth.isAuthenticated ? { name: 'dashboard' } : true
  if (!auth.isAuthenticated) return { name: 'login' }
  if (!auth.user) {
    try { await auth.fetchMe() } catch { await auth.logout(); return { name: 'login' } }
  }
  return true
})

export default router
