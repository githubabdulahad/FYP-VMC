import { useEffect, useState } from "react";
import { useAuthStore } from "../../../store/authStore";
import { getMe, updateMyProfile } from "../api/authApi";

export default function ProfilePage() {
  const { user, setUser } = useAuthStore();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const displayName = [firstName, lastName].filter(Boolean).join(" ").trim() || user?.username || "Medical Coder";
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "MC";

  useEffect(() => {
    if (!user) {
      getMe()
        .then((freshUser) => {
          setUser(freshUser);
          setFirstName(freshUser.first_name ?? "");
          setLastName(freshUser.last_name ?? "");
          setEmail(freshUser.email ?? "");
        })
        .catch(() => undefined);
      return;
    }

    setFirstName(user.first_name ?? "");
    setLastName(user.last_name ?? "");
    setEmail(user.email ?? "");
  }, [user, setUser]);

  const handleSave = async () => {
    setMessage(null);
    setError(null);
    setIsSaving(true);

    try {
      const updatedUser = await updateMyProfile({
        first_name: firstName,
        last_name: lastName,
        email,
        ...(currentPassword || newPassword || confirmNewPassword
          ? {
              current_password: currentPassword,
              new_password: newPassword,
              confirm_new_password: confirmNewPassword,
            }
          : {}),
      });

      setUser(updatedUser);
      setMessage("Profile updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err) {
      setError("Failed to update profile. Please check your inputs and try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="relative max-w-6xl space-y-6 overflow-hidden">
      <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-teal-100/60 blur-3xl" />
      <div className="absolute top-24 -left-28 h-72 w-72 rounded-full bg-slate-200/60 blur-3xl" />

      <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-teal-900 px-6 py-7 text-white shadow-sm sm:px-8">
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-4">
            <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em] text-teal-100">
              Account Center
            </span>
            <div>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Profile</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300 sm:text-base">
                Keep your identity, contact details, and password in sync with the coding workspace.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/10 px-4 py-4 backdrop-blur">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-lg font-semibold text-slate-950 shadow-sm">
              {initials}
            </div>
            <div>
              <p className="text-lg font-medium text-white">{displayName}</p>
              <p className="text-sm text-slate-300">{user?.role || "coder"}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="relative grid gap-6 lg:grid-cols-[1fr_1.35fr]">
        <div className="space-y-6">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-slate-50 px-6 py-5">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Account Summary</p>
            </div>
            <div className="px-6 py-6 space-y-6">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-600 text-xl font-semibold text-white shadow-sm">
                  {initials}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-xl font-semibold text-slate-900">{displayName}</p>
                  <p className="text-sm text-slate-500">{user?.email || "No email on file"}</p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">Username</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{user?.username ?? "—"}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-4">
                  <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">Role</p>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{user?.role ?? "—"}</p>
                </div>
              </div>

              <div className="rounded-2xl border border-teal-100 bg-teal-50 px-4 py-4 text-sm text-teal-900">
                <p className="font-medium">Profile tip</p>
                <p className="mt-1 text-teal-800/90">
                  Change your password only if you are on a trusted device. Password updates require your current password.
                </p>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="bg-slate-50 px-6 py-5">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Security</p>
            </div>
            <div className="space-y-3 px-6 py-6 text-sm text-slate-600">
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                <span>Current password required for password change</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm">Enabled</span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                <span>JWT cookie authentication</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm">Active</span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                <span>Profile updates</span>
                <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm">Protected</span>
              </div>
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="bg-slate-50 px-6 py-5">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Edit Profile</p>
          </div>

          <div className="space-y-6 px-6 py-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2">
                <span className="block text-sm font-medium text-slate-700">First name</span>
                <input
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100"
                />
              </label>
              <label className="space-y-2">
                <span className="block text-sm font-medium text-slate-700">Last name</span>
                <input
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100"
                />
              </label>
            </div>

            <label className="space-y-2 block">
              <span className="block text-sm font-medium text-slate-700">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:bg-white focus:ring-4 focus:ring-teal-100"
              />
            </label>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
              <div className="mb-4">
                <p className="text-sm font-semibold text-slate-900">Change password</p>
                <p className="mt-1 text-xs text-slate-500">
                  Leave these fields empty if you only want to update your name or email.
                </p>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <label className="space-y-2 block">
                  <span className="block text-sm font-medium text-slate-700">Current password</span>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:ring-4 focus:ring-teal-100"
                  />
                </label>
                <label className="space-y-2 block">
                  <span className="block text-sm font-medium text-slate-700">New password</span>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:ring-4 focus:ring-teal-100"
                  />
                </label>
                <label className="space-y-2 block">
                  <span className="block text-sm font-medium text-slate-700">Confirm new password</span>
                  <input
                    type="password"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-teal-400 focus:ring-4 focus:ring-teal-100"
                  />
                </label>
              </div>
            </div>

            {message && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
                {message}
              </div>
            )}

            {error && (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex items-center justify-between gap-3 border-t border-slate-200 pt-5">
              <p className="text-xs text-slate-500">
                Changes are saved directly to your authenticated account.
              </p>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSaving && (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                )}
                {isSaving ? "Saving..." : "Save profile"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}