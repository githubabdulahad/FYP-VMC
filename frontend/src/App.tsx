import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';
import { LoginPage } from '@/pages/auth/LoginPage';
import { RegisterPage } from '@/pages/auth/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { SubmitPage } from '@/pages/SubmitPage';
import { ProcessingPage } from '@/pages/ProcessingPage';
import { ResultsListPage } from '@/pages/ResultsListPage';
import { ResultDetailPage } from '@/pages/ResultDetailPage';
import { ReviewQueuePage } from '@/pages/ReviewQueuePage';
import { ReviewDetailPage } from '@/pages/ReviewDetailPage';
import { ReportsListPage } from '@/pages/ReportsListPage';
import { ReportDetailPage } from '@/pages/ReportDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-teal-400 border-t-transparent" />
      </div>
    );
  }
  if (user) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={
                <GuestOnly>
                  <LoginPage />
                </GuestOnly>
              }
            />
            <Route
              path="/register"
              element={
                <GuestOnly>
                  <RegisterPage />
                </GuestOnly>
              }
            />

            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="submit" element={<SubmitPage />} />
              <Route path="processing/:recordId" element={<ProcessingPage />} />
              <Route path="results" element={<ResultsListPage />} />
              <Route path="results/:id" element={<ResultDetailPage />} />
              <Route path="review" element={<ReviewQueuePage />} />
              <Route path="review/:id" element={<ReviewDetailPage />} />
              <Route path="reports" element={<ReportsListPage />} />
              <Route path="reports/:id" element={<ReportDetailPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
