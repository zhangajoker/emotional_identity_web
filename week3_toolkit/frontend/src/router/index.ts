import {
  createRouter,
  createWebHistory,
} from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'capture',
      component: () => import('../views/MoodCaptureView.vue'),
    },
    {
      path: '/timeline',
      name: 'timeline',
      component: () => import('../components/MoodTimelineView.vue'),
    },
    {
      path: '/therapy',
      name: 'therapy',
      component: () => import('../components/CbtBreathingTherapy.vue'),
    },
    {
      path: '/space',
      name: 'space',
      component: () => import('../views/SocialSpaceView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatEntryView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/AccountSettingsView.vue'),
    },
    {
      path: '/u/:userId',
      name: 'personal-space',
      component: () => import('../views/PersonalSpaceView.vue'),
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/ResetPasswordView.vue'),
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('../views/VerifyEmailView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
