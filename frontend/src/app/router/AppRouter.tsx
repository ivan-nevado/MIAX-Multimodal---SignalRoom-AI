import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { Spinner } from '@/components/ui/states';
import LandingPage from '@/pages/LandingPage';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage';
import NotFoundPage from '@/pages/NotFoundPage';
import AboutPage from '@/pages/AboutPage';
import MethodologyPage from '@/pages/MethodologyPage';
import PrivacyPage from '@/pages/PrivacyPage';
import TermsPage from '@/pages/TermsPage';
import { ScrollToHash } from './ScrollToHash';
import { ProtectedRoute } from './ProtectedRoute';

// Application pages are code-split; charts & graph libraries load only when needed.
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const AssetPage = lazy(() => import('@/pages/AssetPage'));
const ResearchPage = lazy(() => import('@/pages/ResearchPage'));
const SearchPage = lazy(() => import('@/pages/SearchPage'));
const InvestigationPage = lazy(() => import('@/pages/InvestigationPage'));
const BriefingPage = lazy(() => import('@/pages/BriefingPage'));
const BriefingsPage = lazy(() => import('@/pages/BriefingsPage'));
const WatchlistPage = lazy(() => import('@/pages/WatchlistPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner />
    </div>
  );
}

export function AppRouter() {
  return (
    <>
      <ScrollToHash />
      <Routes>
        {/* Consistent behaviour: the landing page stays reachable for signed-in users too. */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/methodology" element={<MethodologyPage />} />
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/app/dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <Suspense fallback={<PageFallback />}>
                <DashboardPage />
              </Suspense>
            }
          />
          <Route
            path="asset/:symbol"
            element={
              <Suspense fallback={<PageFallback />}>
                <AssetPage />
              </Suspense>
            }
          />
          <Route
            path="research"
            element={
              <Suspense fallback={<PageFallback />}>
                <ResearchPage />
              </Suspense>
            }
          />
          <Route
            path="search"
            element={
              <Suspense fallback={<PageFallback />}>
                <SearchPage />
              </Suspense>
            }
          />
          <Route
            path="investigation/:id"
            element={
              <Suspense fallback={<PageFallback />}>
                <InvestigationPage />
              </Suspense>
            }
          />
          <Route
            path="briefings"
            element={
              <Suspense fallback={<PageFallback />}>
                <BriefingsPage />
              </Suspense>
            }
          />
          <Route
            path="briefing/:id"
            element={
              <Suspense fallback={<PageFallback />}>
                <BriefingPage />
              </Suspense>
            }
          />
          <Route
            path="watchlist"
            element={
              <Suspense fallback={<PageFallback />}>
                <WatchlistPage />
              </Suspense>
            }
          />
          <Route
            path="settings"
            element={
              <Suspense fallback={<PageFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  );
}
