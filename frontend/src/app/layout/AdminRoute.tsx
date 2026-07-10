import { Navigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

interface Props {
  children: React.ReactNode;
}

/**
 * Gates internal-admin-only screens (e.g. API key provisioning).
 * Must be nested INSIDE ProtectedRoute -- assumes user is already
 * authenticated and useAuthStore().user is populated.
 * Redirects anyone who isn't role="admin" + organization.slug="internal"
 * to the dashboard rather than showing a blank/broken page.
 */
function AdminRoute({ children }: Props) {
  const { user } = useAuthStore();

  const isInternalAdmin =
    user?.role === "admin" && user?.organization?.slug === "internal";

  if (!isInternalAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

export default AdminRoute;