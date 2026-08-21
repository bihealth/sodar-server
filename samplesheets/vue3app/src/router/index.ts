import { createRouter, createWebHashHistory } from 'vue-router'
import StudyView from '../views/StudyView.vue'
import OverviewView from '../views/OverviewView.vue'
import ParserWarningView from '@/views/ParserWarningView.vue'

export const routes = [
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
  ]

const router = createRouter({
  history: createWebHashHistory(),
  routes: routes
})
export default router
