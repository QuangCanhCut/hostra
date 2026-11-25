import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppShell } from '@/app/layouts/AppShell'
import { RouteFallback } from '@/components/shared/RouteFallback'

/* Route-level code splitting via React.lazy (M03 Addendum #4) */
const SignInPage = lazy(() =>
  import('@/features/auth/pages/SignInPage').then((m) => ({ default: m.SignInPage })),
)
const RightsConsentPortalPage = lazy(() =>
  import('@/features/presenter/pages/RightsConsentPortalPage').then((m) => ({
    default: m.RightsConsentPortalPage,
  })),
)
const ViewerLiveRoomPage = lazy(() =>
  import('@/features/viewer/pages/ViewerLiveRoomPage').then((m) => ({
    default: m.ViewerLiveRoomPage,
  })),
)
const DashboardPage = lazy(() =>
  import('@/features/dashboard/pages/DashboardPage').then((m) => ({
    default: m.DashboardPage,
  })),
)
const OnboardingPage = lazy(() =>
  import('@/features/workspace/pages/OnboardingPage').then((m) => ({
    default: m.OnboardingPage,
  })),
)
const PresenterLibraryPage = lazy(() =>
  import('@/features/presenter/pages/PresenterLibraryPage').then((m) => ({
    default: m.PresenterLibraryPage,
  })),
)
const PresenterWizardPage = lazy(() =>
  import('@/features/presenter/pages/PresenterWizardPage').then((m) => ({
    default: m.PresenterWizardPage,
  })),
)
const PresenterDetailPage = lazy(() =>
  import('@/features/presenter/pages/PresenterDetailPage').then((m) => ({
    default: m.PresenterDetailPage,
  })),
)
const ProductsCatalogPage = lazy(() =>
  import('@/features/products/pages/ProductsCatalogPage').then((m) => ({
    default: m.ProductsCatalogPage,
  })),
)
const ProductWizardPage = lazy(() =>
  import('@/features/products/pages/ProductWizardPage').then((m) => ({
    default: m.ProductWizardPage,
  })),
)
const ProductDetailPage = lazy(() =>
  import('@/features/products/pages/ProductDetailPage').then((m) => ({
    default: m.ProductDetailPage,
  })),
)
const KnowledgeLibraryPage = lazy(() =>
  import('@/features/knowledge/pages/KnowledgeLibraryPage').then((m) => ({
    default: m.KnowledgeLibraryPage,
  })),
)
const KnowledgeReviewPage = lazy(() =>
  import('@/features/knowledge/pages/KnowledgeReviewPage').then((m) => ({
    default: m.KnowledgeReviewPage,
  })),
)
const StoryPlannerPage = lazy(() =>
  import('@/features/story-planner/pages/StoryPlannerPage').then((m) => ({
    default: m.StoryPlannerPage,
  })),
)
const SessionsListPage = lazy(() =>
  import('@/features/live-session/pages/SessionsListPage').then((m) => ({
    default: m.SessionsListPage,
  })),
)
const SessionWizardPage = lazy(() =>
  import('@/features/live-session/pages/SessionWizardPage').then((m) => ({
    default: m.SessionWizardPage,
  })),
)
const SessionDetailPage = lazy(() =>
  import('@/features/live-session/pages/SessionDetailPage').then((m) => ({
    default: m.SessionDetailPage,
  })),
)
const ReadinessPage = lazy(() =>
  import('@/features/live-session/pages/ReadinessPage').then((m) => ({
    default: m.ReadinessPage,
  })),
)
const LiveControlRoomPage = lazy(() =>
  import('@/features/control-room/pages/LiveControlRoomPage').then((m) => ({
    default: m.LiveControlRoomPage,
  })),
)
const MembersPage = lazy(() =>
  import('@/features/members/pages/MembersPage').then((m) => ({ default: m.MembersPage })),
)
const InvitesPage = lazy(() =>
  import('@/features/invitations/pages/InvitesPage').then((m) => ({
    default: m.InvitesPage,
  })),
)
const ReportsHistoryPage = lazy(() =>
  import('@/features/reports/pages/ReportsHistoryPage').then((m) => ({
    default: m.ReportsHistoryPage,
  })),
)
const SessionReportPage = lazy(() =>
  import('@/features/reports/pages/SessionReportPage').then((m) => ({
    default: m.SessionReportPage,
  })),
)

function withSuspense(node: ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{node}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/studio/dashboard" replace />,
  },
  {
    path: '/auth/sign-in',
    element: withSuspense(<SignInPage />),
  },
  {
    path: '/rights/consent/:requestId',
    element: withSuspense(<RightsConsentPortalPage />),
  },
  /* M03-D: Viewer Live Room — Standalone mobile-first surface WITHOUT Merchant AppShell */
  {
    path: '/live/:id',
    element: withSuspense(<ViewerLiveRoomPage />),
  },
  {
    path: '/studio',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/studio/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: withSuspense(<DashboardPage />),
      },
      {
        path: 'onboarding',
        element: withSuspense(<OnboardingPage />),
      },
      /* M02-A: AI Presenter Studio */
      {
        path: 'presenters',
        element: withSuspense(<PresenterLibraryPage />),
      },
      {
        path: 'presenters/new',
        element: withSuspense(<PresenterWizardPage />),
      },
      {
        path: 'presenters/:id',
        element: withSuspense(<PresenterDetailPage />),
      },
      /* M02-B: Products & OCOP */
      {
        path: 'products',
        element: withSuspense(<ProductsCatalogPage />),
      },
      {
        path: 'products/new',
        element: withSuspense(<ProductWizardPage />),
      },
      {
        path: 'products/:skuId',
        element: withSuspense(<ProductDetailPage />),
      },
      /* M02-C: Knowledge & Claims */
      {
        path: 'knowledge',
        element: withSuspense(<KnowledgeLibraryPage />),
      },
      {
        path: 'knowledge/:skuId',
        element: withSuspense(<KnowledgeReviewPage />),
      },
      /* M02-D, E, F: Sessions, Story Planner & Readiness */
      {
        path: 'sessions',
        element: withSuspense(<SessionsListPage />),
      },
      {
        path: 'sessions/new',
        element: withSuspense(<SessionWizardPage />),
      },
      {
        path: 'sessions/:id',
        element: withSuspense(<SessionDetailPage />),
      },
      {
        path: 'sessions/:id/setup',
        element: withSuspense(<SessionWizardPage />),
      },
      {
        path: 'sessions/:id/story',
        element: withSuspense(<StoryPlannerPage />),
      },
      {
        path: 'sessions/:id/readiness',
        element: withSuspense(<ReadinessPage />),
      },
      /* M03-A: Live Control Room */
      {
        path: 'sessions/:id/control',
        element: withSuspense(<LiveControlRoomPage />),
      },
      /* M03-C: Invite Management & QR */
      {
        path: 'sessions/:id/invites',
        element: withSuspense(<InvitesPage />),
      },
      {
        path: 'invites/*',
        element: withSuspense(<InvitesPage />),
      },
      /* M03-B: Members & Permissions */
      {
        path: 'members/*',
        element: withSuspense(<MembersPage />),
      },
      /* M03-E: Session Reports & History */
      {
        path: 'sessions/:id/report',
        element: withSuspense(<SessionReportPage />),
      },
      {
        path: 'reports/*',
        element: withSuspense(<ReportsHistoryPage />),
      },
    ],
  },
])
