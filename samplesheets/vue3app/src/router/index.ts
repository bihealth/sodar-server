import { createRouter, createWebHashHistory } from 'vue-router'
import StudyView from '../views/StudyView.vue'
import OverviewView from '../views/OverviewView.vue'
import ParserWarningView from '@/views/ParserWarningView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: { name: 'study'}
    }, // Init version of StudyView before we have study UUID
    {
      path: '/study/:studyUuid?',
      name: 'study',
      component: StudyView
    },
    {
      path: '/study/:studyUuid/assay/:assayUuid',
      name: 'assay',
      component: StudyView
    },
    {
      path: '/overview',
      name: 'overview',
      component: OverviewView
    },
    {
      path: '/warnings',
      name: 'warnings',
      component: ParserWarningView
    }
    /*
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
    */
  ],
})
export default router
