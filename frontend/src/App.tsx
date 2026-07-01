import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { getMe } from "./features/auth/api/authApi";
import { useAuthStore } from "./store/authStore";
import ProtectedRoute from "./app/layout/ProtectedRoute";
import AppLayout from "./app/layout/AppLayout";
import LoginPage from "./features/auth/components/LoginPage";
import SignupPage from "./features/auth/components/SignupPage";
import DashboardPage from "./features/dashboard/components/DashboardPage";
import UploadPage from "./features/upload/components/UploadPage";
import ReviewQueuePage from "./features/review/components/ReviewQueuePage";
import ReviewPage from "./features/review/components/ReviewPage";
import AllRecordsPage from "./features/records/components/AllRecordsPage";

function App() {
const { setUser, clearUser } = useAuthStore();

  useEffect(() => {
    getMe()
      .then((user) => setUser(user))
      .catch(() => clearUser());
      // runs when browser restores page from bfcache (back button)
  const handlePageShow = (e: PageTransitionEvent) => {
    if (e.persisted) {
      getMe()
        .then((user) => setUser(user))
        .catch(() => {
          clearUser();
          window.location.href = "/login";
        });
    }
  };

  window.addEventListener("pageshow", handlePageShow);
  return () => window.removeEventListener("pageshow", handlePageShow);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      {/* Protected routes — all share the AppLayout shell */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/review-queue" element={<ReviewQueuePage />} />
        <Route path="/records" element={<AllRecordsPage/>} />
        <Route path="/review/:id" element={<ReviewPage/>} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;